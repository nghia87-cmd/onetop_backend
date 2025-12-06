# PYTEST MIGRATION STRATEGY

## Mục tiêu
Chuyển đổi toàn bộ test suite từ Django `APITestCase` sang Pytest function-based style để:
- Tận dụng fixtures từ `conftest.py`
- Giảm code duplication (không cần `setUp()` methods)
- Dễ đọc, dễ maintain hơn
- Tăng tốc độ chạy test với `--reuse-db`

## Tiến độ Migration

### ✅ Hoàn thành (Pytest Style)
- [x] `apps/companies/test_pytest_style.py` - Template reference
- [x] `apps/users/test_pytest_style.py` - 24 tests
- [x] `apps/jobs/test_pytest_style.py` - 31 tests

### 🔄 Chưa migrate (Còn dùng APITestCase)
- [ ] `apps/applications/tests.py`
- [ ] `apps/chats/tests.py`
- [ ] `apps/resumes/tests.py`
- [ ] `apps/notifications/tests.py`
- [ ] `apps/payments/tests.py`

## Hướng dẫn Refactor

### Before (APITestCase Style) ❌
```python
from rest_framework.test import APITestCase

class UserAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='pass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_get_profile(self):
        url = reverse('user-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
```

### After (Pytest Style) ✅
```python
import pytest
from rest_framework import status

@pytest.mark.django_db
def test_get_profile(authenticated_client, candidate_user):
    """Test lấy profile khi đã đăng nhập"""
    url = reverse('user-profile')
    response = authenticated_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['email'] == candidate_user.email
```

## Lợi ích

### 1. Code ngắn gọn hơn
- **Before**: 15 dòng (class + setUp + test)
- **After**: 7 dòng (chỉ test function)

### 2. Fixtures tái sử dụng
Các fixtures có sẵn trong `conftest.py`:
- `candidate_user` - User CANDIDATE
- `recruiter_user` - User RECRUITER
- `vip_recruiter_user` - User RECRUITER VIP
- `company` - Company object
- `job` - Job object
- `authenticated_client` - APIClient đã auth với candidate_user
- `api_client` - APIClient chưa auth

### 3. Dễ debug
```bash
# Chạy 1 test cụ thể
pytest apps/users/test_pytest_style.py::test_login_success -v

# Chạy tất cả tests có chứa "login"
pytest -k "login" -v

# Chỉ chạy API tests
pytest -m api -v
```

## Action Items

### Phase 1: Parallel Testing (Tuần này)
- [x] Tạo `test_pytest_style.py` song song với `tests.py`
- [x] Đảm bảo coverage không giảm
- [x] Team làm quen với pytest syntax

### Phase 2: Deprecation (Tuần sau)
- [ ] Thêm deprecation warning vào các file `tests.py` cũ
- [ ] Update CI/CD chỉ chạy `test_pytest_style.py`

### Phase 3: Cleanup (Cuối tháng)
- [ ] Xóa toàn bộ file `tests.py` cũ
- [ ] Rename `test_pytest_style.py` → `tests.py`
- [ ] Update documentation

## Running Tests

```bash
# Chạy tất cả tests mới (pytest style)
pytest apps/users/test_pytest_style.py apps/jobs/test_pytest_style.py -v

# Chạy tất cả tests (cả cũ lẫn mới)
pytest apps/ -v

# Chạy với coverage
pytest apps/ --cov=apps --cov-report=html

# Chỉ chạy pytest style tests
pytest apps/**/test_pytest_style.py -v
```

## Checklist cho Refactor

Khi refactor một app từ `tests.py` → `test_pytest_style.py`:

- [ ] Import `pytest` và `@pytest.mark.django_db`
- [ ] Thay `self.assertEqual()` → `assert`
- [ ] Thay `self.assertTrue()` → `assert condition`
- [ ] Thay `self.assertIn()` → `assert item in collection`
- [ ] Xóa class `TestCase`, chuyển thành functions
- [ ] Xóa `setUp()`, dùng fixtures từ `conftest.py`
- [ ] Thay `self.client` → `api_client` hoặc `authenticated_client`
- [ ] Thêm docstring cho mỗi test function
- [ ] Chạy test đảm bảo pass: `pytest apps/app_name/test_pytest_style.py -v`

## Contact
Nếu có thắc mắc về migration, tham khảo:
- File template: `apps/companies/test_pytest_style.py`
- Pytest docs: https://docs.pytest.org/
- Pytest-django: https://pytest-django.readthedocs.io/
