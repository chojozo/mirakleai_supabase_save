# mirakleai_supabase_save

## 프로젝트 개요
이 프로젝트는 웹 크롤러로, 특정 데이터를 수집하여 Supabase 데이터베이스에 저장하는 기능을 수행합니다.

## 설정
프로젝트를 실행하기 전에 다음 단계를 따라 환경을 설정해야 합니다.

1.  **Python 환경 설정**: Python 3.x가 설치되어 있는지 확인합니다.
2.  **의존성 설치**: `requirements.txt` 파일에 명시된 모든 Python 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```
3.  **.env 파일 설정**: 프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 Supabase 연결 정보를 포함한 필요한 환경 변수를 설정합니다. 예시:
    ```
    SUPABASE_URL="YOUR_SUPABASE_URL"
    SUPABASE_KEY="YOUR_SUPABASE_ANON_KEY"
    # 기타 필요한 환경 변수
    ```

## 사용법
크롤러를 실행하려면 다음 명령을 사용합니다:

```bash
python mk_crawler.py
```

`run_report_generator.bat` 파일을 통해 실행할 수도 있습니다.

## GitHub Actions
이 프로젝트는 `.github/workflows/crawler.yml` 파일을 통해 GitHub Actions 워크플로우를 포함하고 있습니다. 이 워크플로우는 크롤러의 자동 실행 및 배포를 관리할 수 있습니다.
