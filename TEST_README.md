# Unit Testing Guide - OneTop Backend

## 📋 Tổng quan

Dự án đã được trang bị bộ unit test toàn diện cho các modules chính:

- ✅ **Users App** - Authentication, Registration, User Profile
- ✅ **Jobs App** - Job CRUD, SavedJob, Elasticsearch Search
- ✅ **Applications App** - Application workflow, Interview Schedule
- ✅ **Companies App** - Company management
- ✅ **Payments App** - Service Packages, Transactions, VNPay

## 🚀 Cài đặt môi trường test

### 1. Cài đặt pytest và các dependencies

```bash
pip install pytest pytest-django pytest-cov factory-boy faker
```

### 2. Cấu hình đã có sẵn

- `pytest.ini` - Cấu hình pytest
- `conftest.py` - Fixtures dùng chung

## 🧪 Chạy Tests

### Chạy tất cả tests

```bash
# Sử dụng pytest (khuyến nghị)
pytest

# Hoặc sử dụng Django test runner
python manage.py test
```

### Chạy test cho 1 app cụ thể

```bash
# Test Users app
pytest apps/users/tests.py

# Test Jobs app
pytest apps/jobs/tests.py

# Test Applications app
pytest apps/applications/tests.py

# Test Companies app
pytest apps/companies/tests.py

# Test Payments app
pytest apps/payments/tests.py
```

### Chạy test với coverage report

```bash
# Coverage cho toàn bộ dự án
pytest --cov=apps --cov-report=html

# Coverage cho 1 app cụ thể
pytest --cov=apps.users --cov-report=html apps/users/tests.py

# Xem report trong trình duyệt
# Mở file: htmlcov/index.html
```

### Chạy test chi tiết với verbose

```bash
pytest -v
pytest -vv  # Extra verbose
```

### Chạy test theo markers

```bash
# Chỉ chạy unit tests
pytest -m unit

# Chỉ chạy API tests
pytest -m api

# Bỏ qua slow tests
pytest -m "not slow"
```

### Chạy test cụ thể

```bash
# Chạy 1 test class
pytest apps/users/tests.py::UserModelTest

# Chạy 1 test method
pytest apps/users/tests.py::UserModelTest::test_user_creation

# Chạy tests có tên chứa keyword
pytest -k "login"
```

## 📊 Test Coverage

Mục tiêu coverage: **≥ 80%**

### Kiểm tra coverage hiện tại

```bash
pytest --cov=apps --cov-report=term-missing
```

### Xuất coverage report

```bash
# HTML report (chi tiết nhất)
pytest --cov=apps --cov-report=html

# Terminal report
pytest --cov=apps --cov-report=term

# XML report (cho CI/CD)
pytest --cov=apps --cov-report=xml
```

## 🔍 Cấu trúc Test Files

### Users App Tests (`apps/users/tests.py`)

- **UserModelTest** - Test User model
- **RegisterAPITest** - Test đăng ký API
- **LoginAPITest** - Test đăng nhập API
- **UserProfileAPITest** - Test profile API

### Jobs App Tests (`apps/jobs/tests.py`)

- **JobModelTest** - Test Job model
- **JobAPITest** - Test Job CRUD API
- **SavedJobAPITest** - Test Saved Job API

### Applications App Tests (`apps/applications/tests.py`)

- **ApplicationModelTest** - Test Application model
- **ApplicationAPITest** - Test Application API
- **InterviewScheduleModelTest** - Test InterviewSchedule model
- **InterviewScheduleAPITest** - Test Interview API

### Companies App Tests (`apps/companies/tests.py`)

- **CompanyModelTest** - Test Company model
- **CompanyAPITest** - Test Company API

### Payments App Tests (`apps/payments/tests.py`)

- **ServicePackageModelTest** - Test ServicePackage model
- **TransactionModelTest** - Test Transaction model
- **PaymentAPITest** - Test Payment API
- **VNPayIntegrationTest** - Test VNPay integration

## 🎯 Test Patterns & Best Practices

### 1. Sử dụng Fixtures (conftest.py)

```python
def test_something(candidate_user, api_client):
    api_client.force_authenticate(user=candidate_user)
    # Test code here
```

### 2. Test Naming Convention

```python
def test_[action]_[expected_result]():
    # Good examples:
    # test_create_job_success
    # test_login_invalid_credentials
    # test_update_profile_readonly_fields
```

### 3. AAA Pattern (Arrange-Act-Assert)

```python
def test_create_application():
    # Arrange
    user = create_user()
    job = create_job()
    
    # Act
    response = client.post('/api/applications/', {...})
    
    # Assert
    assert response.status_code == 201
    assert Application.objects.count() == 1
```

### 4. Test Isolation

Mỗi test phải độc lập, không phụ thuộc vào test khác.

```python
def setUp(self):
    # Tạo fresh data cho mỗi test
    self.user = User.objects.create_user(...)
```

## 🐛 Debug Tests

### Chạy test với pdb debugger

```bash
pytest --pdb  # Dừng tại lỗi đầu tiên
pytest --pdb --maxfail=1  # Dừng sau 1 lỗi
```

### Print debug info trong test

```python
def test_something():
    print(f"Debug: {some_variable}")
    pytest -s  # Chạy với -s để hiện print
```

### Xem output SQL queries

```python
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_with_queries():
    from django.db import connection
    print(connection.queries)
```

## 🔧 Tích hợp CI/CD

### GitHub Actions example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=apps --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 📝 Thêm Tests Mới

### 1. Thêm test cho model mới

```python
class MyModelTest(TestCase):
    def setUp(self):
        self.instance = MyModel.objects.create(...)
    
    def test_model_creation(self):
        self.assertEqual(self.instance.field, expected_value)
```

### 2. Thêm test cho API endpoint mới

```python
class MyAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('my-endpoint')
    
    def test_endpoint_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
```

## 🎓 Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [DRF Testing Guide](https://www.django-rest-framework.org/api-guide/testing/)

## ⚠️ Lưu ý quan trọng

1. **Không test với production database** - Tests tự động dùng test database
2. **Clean test data** - setUp/tearDown tự động xử lý
3. **Mock external services** - Mock VNPay, Elasticsearch khi test
4. **Fast tests** - Tránh sleep(), dùng mock cho async tasks

## 📞 Support

Nếu có vấn đề với tests, kiểm tra:

1. Database migrations đã chạy chưa: `python manage.py migrate`
2. Dependencies đã cài đủ chưa: `pip install -r requirements.txt`
3. Settings test có đúng không: `DJANGO_SETTINGS_MODULE=onetop_backend.settings`

---

**Happy Testing! 🚀**
