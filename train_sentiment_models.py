import pandas as pd
import torch
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
from sklearn.model_selection import train_test_split

from sklearn.metrics import (
    accuracy_score, 
    precision_recall_fscore_support,
    confusion_matrix
)
from sklearn.utils import resample # ## [추가] 샘플링을 위한 import
import os
import re
import warnings
from datetime import datetime

# 경고 메시지 숨기기
warnings.filterwarnings("ignore")

# --- 1. 기본 설정 ---

DEBUG_MODE = False # True: 100개 샘플로 테스트 / False: 전체 데이터로 학습

CSV_PATH = 'verified_data.csv' 
MODEL_LIST = ["beomi/kcbert-large", "klue/roberta-large"]

# ## [추가] 1순위였던 2가지 불균형 해소 전략을 리스트로 정의
SAMPLING_STRATEGIES = ["oversampling", "undersampling"] 

# 3-Label 설정
LABEL2ID = {"neutral": 0, "negative": 1, "positive": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
LABELS_LIST = list(LABEL2ID.keys())

LOG_FILE_PATH = "evaluation_results.txt" 
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- 2. 데이터 전처리 단계 (리팩토링) ---

def load_csv_data(csv_path):
    """(신규) 1. CSV 로드 및 기본 전처리"""
    try:
        data_df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ 오류: '{csv_path}' 파일을 찾을 수 없습니다.")
        return None

    # 3-Label 필터링 및 매핑
    data_df = data_df[data_df['label'].isin(LABELS_LIST)]
    data_df['label'] = data_df['label'].map(LABEL2ID)
    data_df = data_df.dropna(subset=['text', 'label'])
    data_df['text'] = data_df['text'].astype(str)

    if len(data_df) < 10:
        print("❌ 오류: 학습에 유효한 데이터가 10건 미만입니다.")
        return None

    # ## [수정] DEBUG_MODE 로직 (head 대신 sample 사용)
    if DEBUG_MODE:
        print("\n*********************************************************")
        print("           ⚠️ [검사 모드]가 활성화되었습니다. ⚠️")
        print("     (100개 데이터 샘플로 1 에포크만 빠르게 테스트합니다)")
        print("*********************************************************\n")
        if len(data_df) > 100:
            # head(100) 대신 무작위 100개를 뽑아야 3-Label이 포함될 확률이 높음
            data_df = data_df.sample(n=100, random_state=42) 
        else:
            print("경고: 전체 데이터가 100개 미만입니다.")
    
    print(f"원본 데이터 로드 완료: 총 {len(data_df)}건")
    return data_df

def get_balanced_data(data_df, strategy):
    """(신규) 2. (1순위 해결) 샘플링 전략 적용"""
    
    df_neutral = data_df[data_df.label == LABEL2ID['neutral']]
    df_negative = data_df[data_df.label == LABEL2ID['negative']]
    df_positive = data_df[data_df.label == LABEL2ID['positive']]

    if strategy == "oversampling":
        # 가장 많은 클래스 찾기 (DEBUG_MODE가 켜져도 동작하도록)
        max_size = max(len(df_neutral), len(df_negative), len(df_positive))
        
        df_neutral_sampled = resample(df_neutral, replace=True, n_samples=max_size, random_state=123)
        df_negative_sampled = resample(df_negative, replace=True, n_samples=max_size, random_state=123)
        df_positive_sampled = resample(df_positive, replace=True, n_samples=max_size, random_state=123)
        
        df_balanced = pd.concat([df_neutral_sampled, df_negative_sampled, df_positive_sampled])
        print(f"  [Oversampling] 적용 완료: 총 {len(df_balanced)}건 (각 클래스 {max_size}건)")

    elif strategy == "undersampling":
        # 가장 적은 클래스 찾기
        min_size = min(len(df_neutral), len(df_negative), len(df_positive))
        if min_size == 0:
             print("❌ [Undersampling] 오류: 데이터가 0개인 클래스가 있어 실행 불가능합니다.")
             return None

        df_neutral_sampled = resample(df_neutral, replace=False, n_samples=min_size, random_state=123)
        df_negative_sampled = resample(df_negative, replace=False, n_samples=min_size, random_state=123)
        df_positive_sampled = resample(df_positive, replace=False, n_samples=min_size, random_state=123)

        df_balanced = pd.concat([df_neutral_sampled, df_negative_sampled, df_positive_sampled])
        print(f"  [Undersampling] 적용 완료: 총 {len(df_balanced)}건 (각 클래스 {min_size}건)")
        
    else:
        print("경고: 샘플링 전략이 지정되지 않았습니다. 원본 데이터를 사용합니다.")
        df_balanced = data_df

    return df_balanced

def split_data_8_1_1(df_balanced):
    """(신규) 3. (2순위 해결) 데이터를 80(학습)/10(검증)/10(테스트)로 분리"""
    
    # 1차 분리: Train (80%) / Temp (20%)
    train_df, temp_df = train_test_split(
        df_balanced, 
        test_size=0.2,
        random_state=42,
        stratify=df_balanced['label']
    )
    
    # 2차 분리: Validation (10%) / Test (10%)
    try:
        val_df, test_df = train_test_split(
            temp_df, 
            test_size=0.5, # 20%의 절반 = 10%
            random_state=42,
            stratify=temp_df['label']
        )
    except ValueError:
        print("경고: 데이터가 너무 적어 (검증/테스트) 분리 비율을 유지하지 못했습니다.")
        # 데이터가 너무 적으면(예: 총 23개 미만) stratify가 불가능할 수 있음
        val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)

    print(f"데이터 분리 완료 (80/10/10):")
    print(f"  - 학습(Train): {len(train_df)}건")
    print(f"  - 검증(Validation): {len(val_df)}건")
    print(f"  - 테스트(Test): {len(test_df)}건")
    
    return (
        Dataset.from_pandas(train_df.reset_index(drop=True)),
        Dataset.from_pandas(val_df.reset_index(drop=True)),
        Dataset.from_pandas(test_df.reset_index(drop=True))
    )

def tokenize_function(examples, tokenizer):
    cleaned_text = [re.sub(r'[^가-힣0-9?.!]', ' ', str(text)) for text in examples['text']]
    cleaned_text = [re.sub(r'\s+', ' ', text).strip() for text in cleaned_text]
    
    return tokenizer(
        cleaned_text, 
        padding="max_length",
        truncation=True,
        max_length=128
    )

# --- 3. 평가 및 분석 함수 단계 ---

def compute_metrics(p):
    preds = np.argmax(p.predictions, axis=1)
    labels = p.label_ids
    
    acc = accuracy_score(labels, preds)
    
    # ▼▼▼ [수정 2] 올바른 함수 이름으로 수정 ▼▼▼
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average='weighted', zero_division=0
    )
    # ▲▲▲ 수정 완료 ▲▲▲
    
    cm = confusion_matrix(labels, preds, labels=list(LABEL2ID.values()))
    
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall,
        'confusion_matrix': cm.tolist()
    }

def print_and_analyze_cm(metrics, stage, model_name, strategy_name):
    """혼동 행렬 출력 (전략 이름[strategy_name] 추가)"""
    def log_message(message, file_handle):
        print(message)
        file_handle.write(message + "\n")

    acc = metrics.get('eval_accuracy', metrics.get('accuracy', 0))
    f1 = metrics.get('eval_f1', metrics.get('f1', 0))
    cm_list = metrics.get('eval_confusion_matrix', metrics.get('confusion_matrix', []))
    cm = np.array(cm_list)

    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        # ## [수정] 로그에 전략 이름(oversampling 등)이 포함되도록 수정
        log_message(f"\n--- [{model_name} / {strategy_name.upper()} / {stage}] 평가 결과 ---", f)
        log_message(f"  [정확도]: {acc:.4f}", f)
        log_message(f"  [F1-Score (Weighted)]: {f1:.4f}", f)
        
        if not cm_list or not cm.any():
            log_message("  [혼동 행렬을 계산할 수 없습니다.]", f)
            return

        log_message("\n  [혼동 행렬 (Confusion Matrix)]:", f)
        
        header = " " * 10 + " ".join([f"{label+'(예측)':<10}" for label in LABELS_LIST])
        log_message(header, f)
        log_message(" " * 10 + "-" * (len(LABELS_LIST) * 11), f)
        
        for i, label in enumerate(LABELS_LIST):
            row_str = f"{label + '(실제)':<10}"
            if i < len(cm):
                for j, val in enumerate(cm[i]):
                    if j < len(cm[i]):
                        row_str += f" {val:<10}"
                    else:
                        row_str += " " * 11
            log_message(row_str, f)

        log_message("\n  [분석 요약]:", f)
        log_message(f"  - 모델이 3개의 레이블{LABELS_LIST}을 기반으로 평가되었습니다.", f)


# --- 4. 메인 실행 로직 단계 ---

def run_training_evaluation():
    
    log_prefix = "[검사 모드] " if DEBUG_MODE else "[실제 학습] "
    
    # ## [수정] 로그 파일을 'w' (새로 쓰기) 모드로 열어 이전 로그를 초기화
    with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(f"=========================================================\n")
        f.write(f"{log_prefix}캡스톤 프로젝트 모델 학습 로그 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
        f.write(f"사용 장치: {DEVICE}\n")
        f.write(f"=========================================================\n")
    print(f"=========================================================")
    print(f"{log_prefix}사용 장치: {DEVICE}")
    print(f"평가 결과는 {LOG_FILE_PATH} 파일에 새로 저장됩니다.")
    print(f"=========================================================")

    # 단계 1: 데이터 로드 (한 번만)
    base_df = load_csv_data(CSV_PATH)
    if base_df is None:
        return

    # ## [추가] 단계 2: 정의된 샘플링 전략별로 순차 실행
    for strategy in SAMPLING_STRATEGIES:
        
        print(f"\n=========================================================")
        print(f"======= [전략: {strategy.upper()}] 테스트 시작 =======")
        print(f"=========================================================")
        
        # 단계 2-1: (1순위) 데이터 불균형 해소
        balanced_df = get_balanced_data(base_df, strategy)
        if balanced_df is None:
            continue # (예: 언더샘플링 시 0개 데이터가 있어 실패한 경우)

        # 단계 2-2: (2순위) 데이터 분리 (80/10/10)
        train_dataset, val_dataset, test_dataset = split_data_8_1_1(balanced_df)

        # 단계 2-3: 모델별 순차 학습
        for model_name in MODEL_LIST:
            print(f"\n=========================================================")
            print(f"{log_prefix}모델: {model_name} (전략: {strategy.upper()})")
            print(f"=========================================================")

            try:
                tokenizer = AutoTokenizer.from_pretrained(model_name)
            except Exception as e:
                print(f"❌ 오류: {model_name} 토크나이저 로드 실패. {e}")
                continue
            
            tokenized_train_dataset = train_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
            tokenized_val_dataset = val_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
            tokenized_test_dataset = test_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)

            # 단계 2-3-1: (학습 전) 평가 (Test Set)
            print(f"\n>>> [{log_prefix}단계 1/4] (학습 전) Pre-trained 모델 성능 평가...")
            
            try:
                pre_trained_model = AutoModelForSequenceClassification.from_pretrained(
                    model_name, 
                    num_labels=len(LABEL2ID), 
                    label2id=LABEL2ID, 
                    id2label=ID2LABEL,
                    ignore_mismatched_sizes=True
                ).to(DEVICE)
            except Exception as e:
                print(f"❌ 오류: {model_name} 모델 로드 실패. {e}")
                continue

            eval_trainer = Trainer(
                model=pre_trained_model,
                args=TrainingArguments(output_dir="./eval_temp", per_device_eval_batch_size=16, report_to="none"),
                eval_dataset=tokenized_test_dataset, # (최종) 테스트셋으로 학습 전 성능 평가
                compute_metrics=compute_metrics,
                data_collator=DataCollatorWithPadding(tokenizer=tokenizer)
            )
            
            pre_metrics = eval_trainer.evaluate()
            print_and_analyze_cm(pre_metrics, "학습 전 (Pre-trained) - Test Set", model_name, strategy)

            # 단계 2-3-2: (학습 후) Fine-Tuning
            print(f"\n>>> [{log_prefix}단계 2/4] (학습 후) Fine-Tuning 시작...")
            
            del pre_trained_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            fine_tune_model = AutoModelForSequenceClassification.from_pretrained(
                model_name, 
                num_labels=len(LABEL2ID), 
                label2id=LABEL2ID, 
                id2label=ID2LABEL,
                ignore_mismatched_sizes=True
            ).to(DEVICE)
            
            output_model_dir = f"./{model_name.replace('/', '_')}-{strategy}-finetuned"
            
            if DEBUG_MODE:
                training_epochs = 1
                train_batch_size = 2
                logging_steps = 1
            else:
                training_epochs = 3
                train_batch_size = 8
                logging_steps = 10

            training_args = TrainingArguments(
                output_dir=output_model_dir,
                num_train_epochs=training_epochs, 
                per_device_train_batch_size=train_batch_size, 
                per_device_eval_batch_size=16,
                eval_strategy="epoch", # '검증(Validation)' 데이터셋으로 1 에포크마다 평가
                save_strategy="epoch",
                load_best_model_at_end=True, # '검증' 데이터 기준 최고 F1 모델 저장
                logging_dir='./logs',
                logging_steps=logging_steps, 
                metric_for_best_model="f1",
                report_to="none",
            )
            
            trainer = Trainer(
                model=fine_tune_model,
                args=training_args,
                train_dataset=tokenized_train_dataset, # 학습용
                eval_dataset=tokenized_val_dataset,   # 검증용 (Best 모델 선발 기준)
                compute_metrics=compute_metrics,
                data_collator=DataCollatorWithPadding(tokenizer=tokenizer)
            )
            
            try:
                trainer.train()
            except torch.cuda.OutOfMemoryError:
                print(f"❌ {model_name} 학습 중 GPU 메모리 부족(OOM) 오류 발생.")
                print("   -> per_device_train_batch_size를 4 또는 2로 줄여보세요.")
                continue
            except Exception as e:
                print(f"❌ {model_name} 학습 중 오류 발생: {e}")
                continue

            # 단계 2-3-3: (학습 후) 검증 데이터 평가 (Best 모델 기준)
            print(f"\n>>> [{log_prefix}단계 3/4] (학습 후) Fine-tuned 모델 검증 평가...")
            post_metrics_val = trainer.evaluate(eval_dataset=tokenized_val_dataset)
            print_and_analyze_cm(post_metrics_val, "학습 후 (Fine-tuned) - Validation Set", model_name, strategy)

            # 단계 2-3-4: (학습 후) ★ 최종 테스트 데이터 평가 ★
            print(f"\n>>> [{log_prefix}단계 4/4] (학습 후) ★ 최종 모델 성능 평가 (Test Set) ★")
            post_metrics_test = trainer.evaluate(eval_dataset=tokenized_test_dataset)
            print_and_analyze_cm(post_metrics_test, "★ 최종 성능 (Fine-tuned) - Test Set ★", model_name, strategy)
            
            best_model_path = os.path.join(output_model_dir, "best_model")
            trainer.save_model(best_model_path)
            print(f"\n✅ Fine-tuned 모델 저장 완료: {best_model_path}")
            
            del fine_tune_model
            del trainer
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

if __name__ == "__main__":
    run_training_evaluation()