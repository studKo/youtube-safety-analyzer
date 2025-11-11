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
    precision_recall_f1_score, 
    confusion_matrix
)
import os
import re
import warnings
from datetime import datetime

# 경고 메시지 숨기기
warnings.filterwarnings("ignore")

# --- 1. 기본 설정 ---

#  1. [검사 모드] 
# True: 20개 데이터로 1 에포크만 훈련하여 코드 전체를 '빠르게 검사'합니다.
# False: verified_data.csv '전체' 데이터로 '실제 학습'을 진행합니다.
DEBUG_MODE = True

CSV_PATH = 'verified_data.csv' 
MODEL_LIST = ["beomi/kcbert-large", "klue/roberta-large"]
LABEL2ID = {"neutral": 0, "negative": 1}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
LABELS_LIST = list(LABEL2ID.keys())

LOG_FILE_PATH = "evaluation_results.txt" 
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- 2. 데이터 전처리 단계 ---

def load_and_prepare_data(csv_path):
    """CSV를 로드하고 학습/평가 세트로 분리합니다."""
    try:
        data_df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ 오류: '{csv_path}' 파일을 찾을 수 없습니다.")
        return None, None

    original_count = len(data_df)
    data_df = data_df[data_df['label'].isin(LABELS_LIST)]
    filtered_count = len(data_df)
    if original_count > filtered_count:
        print(f"알림: {original_count - filtered_count}개의 행이 정의되지 않은 레이블을 가져 제외됩니다.")

    data_df['label'] = data_df['label'].map(LABEL2ID)
    data_df = data_df.dropna(subset=['text', 'label'])
    data_df['text'] = data_df['text'].astype(str)

    if len(data_df) < 10:
        print("❌ 오류: 학습에 유효한 데이터가 10건 미만입니다.")
        return None, None

    # 📍 2. [검사 모드] 활성화 시, 20개 데이터만 샘플로 사용
    if DEBUG_MODE:
        print("\n*********************************************************")
        print("           ⚠️ [검사 모드]가 활성화되었습니다. ⚠️")
        print("     (20개 데이터 샘플로 1 에포크만 빠르게 테스트합니다)")
        print("*********************************************************\n")
        if len(data_df) > 20:
            data_df = data_df.head(20) # 📍 20개 데이터만 샘플링
        else:
            print("경고: 전체 데이터가 20개 미만입니다.")

    try:
        train_df, test_df = train_test_split(
            data_df, 
            test_size=0.2,
            random_state=42,
            stratify=data_df['label']
        )
    except ValueError:
        print("경고: [검사 모드] 데이터가 너무 적어 레이블 비율(stratify)을 유지하지 못했습니다.")
        train_df, test_df = train_test_split(
            data_df, 
            test_size=0.2, 
            random_state=42
        )

    train_dataset = Dataset.from_pandas(train_df.reset_index(drop=True))
    test_dataset = Dataset.from_pandas(test_df.reset_index(drop=True))
    
    print(f"데이터 로드 완료: 총 {len(data_df)}건 (학습용)")
    print(f"학습 데이터: {len(train_dataset)}건, 평가 데이터: {len(test_dataset)}건")
    
    return train_dataset, test_dataset

def tokenize_function(examples, tokenizer):
    cleaned_text = [re.sub(r'[^가-힣0-9?.!]', ' ', str(text)) for text in examples['text']]
    cleaned_text = [re.sub(r'\s+', ' ', text).strip() for text in cleaned_text]
    
    return tokenizer(
        cleaned_text, 
        padding="max_length",
        truncation=True,
        max_length=128
    )

# --- 3. 평가 및 분석 함수 단계 (이전과 동일) ---

def compute_metrics(p):
    preds = np.argmax(p.predictions, axis=1)
    labels = p.label_ids
    
    acc = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_f1_score(
        labels, preds, average='weighted', zero_division=0
    )
    cm = confusion_matrix(labels, preds, labels=list(LABEL2ID.values()))
    
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall,
        'confusion_matrix': cm.tolist()
    }

def print_and_analyze_cm(metrics, stage, model_name):
    """혼동 행렬을 '출력'하고 '파일에 저장'하며 경향을 분석합니다."""
    def log_message(message, file_handle):
        print(message)
        file_handle.write(message + "\n")

    acc = metrics.get('eval_accuracy', metrics.get('accuracy', 0))
    f1 = metrics.get('eval_f1', metrics.get('f1', 0))
    cm_list = metrics.get('eval_confusion_matrix', metrics.get('confusion_matrix', []))
    cm = np.array(cm_list)

    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        log_message(f"\n--- [{model_name} / {stage}] 평가 결과 분석 ---", f)
        log_message(f"  [정확도]: {acc:.4f}", f)
        log_message(f"  [F1-Score (Weighted)]: {f1:.4f}", f)
        
        if not cm_list.any():
            log_message("  [혼동 행렬을 계산할 수 없습니다.]", f)
            return

        log_message("\n  [혼동 행렬 (Confusion Matrix)]:", f)
        header = " " * 10 + " ".join([f"{label+'(예측)':<10}" for label in LABELS_LIST])
        log_message(header, f)
        log_message(" " * 10 + "-" * (len(LABELS_LIST) * 11), f)
        
        for i, label in enumerate(LABELS_LIST):
            row_str = f"{label + '(실제)':<10}"
            for val in cm[i]:
                row_str += f" {val:<10}"
            log_message(row_str, f)

        log_message("\n  [오분류 경향 분석 (negative=1, neutral=0 기준)]:", f)
        try:
            over_estimation = cm[LABEL2ID['neutral']][LABEL2ID['negative']]
            log_message(f"  -  (부정)과대평가 (Neutral -> Negative): {over_estimation} 건", f)
        except (KeyError, IndexError): pass

        try:
            under_estimation = cm[LABEL2ID['negative']][LABEL2ID['neutral']]
            log_message(f"  -  (부정)과소평가 (Negative -> Neutral): {under_estimation} 건", f)
        except (KeyError, IndexError): pass

# --- 4. 메인 실행 로직 단계 ---

def run_training_evaluation():
    
    log_prefix = "[검사 모드] " if DEBUG_MODE else "[실제 학습] "
    
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(f"\n=========================================================\n")
        f.write(f"{log_prefix}캡스톤 프로젝트 모델 학습 로그 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
        f.write(f"사용 장치: {DEVICE}\n")
        f.write(f"=========================================================\n")
    print(f"=========================================================")
    print(f"{log_prefix}사용 장치: {DEVICE}")
    print(f"평가 결과는 {LOG_FILE_PATH} 파일에 영구 저장됩니다.")
    print(f"=========================================================")

    # 단계 1: 데이터 로드
    train_dataset, test_dataset = load_and_prepare_data(CSV_PATH)
    if train_dataset is None:
        return

    # 단계 2: 모델별 순차 학습
    for model_name in MODEL_LIST:
        print(f"\n=========================================================")
        print(f"{log_prefix}모델: {model_name} (순차 진행)")
        print(f"=========================================================")

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            print(f"❌ 오류: {model_name} 토크나이저 로드 실패. {e}")
            continue
        
        tokenized_test_dataset = test_dataset.map(
            lambda x: tokenize_function(x, tokenizer), 
            batched=True
        )

        # 단계 2-1: (학습 전) 평가
        print(f"\n>>> [{log_prefix}단계 2/4] (학습 전) Pre-trained 모델 성능 평가...")
        
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
            args=TrainingArguments(
                output_dir="./eval_temp", 
                per_device_eval_batch_size=16,
                report_to="none"
            ),
            eval_dataset=tokenized_test_dataset,
            compute_metrics=compute_metrics,
            data_collator=DataCollatorWithPadding(tokenizer=tokenizer)
        )
        
        pre_metrics = eval_trainer.evaluate()
        print_and_analyze_cm(pre_metrics, "학습 전 (Pre-trained)", model_name)

        # 단계 2-2: (학습 후) Fine-Tuning
        print(f"\n>>> [{log_prefix}단계 3/4] (학습 후) Fine-Tuning 시작...")
        
        tokenized_train_dataset = train_dataset.map(
            lambda x: tokenize_function(x, tokenizer), 
            batched=True
        )
        
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
        
        output_model_dir = f"./{model_name.replace('/', '_')}-finetuned"
        
        # 📍 3. [검사 모드]에 따라 학습 설정(Epoch, Batch) 조정
        if DEBUG_MODE:
            training_epochs = 1
            train_batch_size = 2 # 16(학습데이터) / 2 = 8 steps. 매우 빠름.
            logging_steps = 1
        else:
            training_epochs = 3 # (실제 학습) 3 에포크
            train_batch_size = 8 # (실제 학습) 배치 크기 8 (GPU 메모리 부족 시 4 또는 2로 줄이세요)
            logging_steps = 10

        training_args = TrainingArguments(
            output_dir=output_model_dir,
            num_train_epochs=training_epochs, # 📍 변수 적용
            per_device_train_batch_size=train_batch_size, # 📍 변수 적용
            per_device_eval_batch_size=16,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            logging_dir='./logs',
            logging_steps=logging_steps, # 📍 변수 적용
            metric_for_best_model="f1",
            report_to="none",
        )
        
        trainer = Trainer(
            model=fine_tune_model,
            args=training_args,
            train_dataset=tokenized_train_dataset,
            eval_dataset=tokenized_test_dataset,
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

        # 단계 2-3: (학습 후) 최종 평가
        print(f"\n>>> [{log_prefix}단계 4/4] (학습 후) Fine-tuned 모델 최종 평가...")
        post_metrics = trainer.evaluate()
        print_and_analyze_cm(post_metrics, "학습 후 (Fine-tuned)", model_name)
        
        best_model_path = os.path.join(output_model_dir, "best_model")
        trainer.save_model(best_model_path)
        print(f"\n✅ Fine-tuned 모델 저장 완료: {best_model_path}")
        
        del fine_tune_model
        del trainer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

if __name__ == "__main__":
    run_training_evaluation()