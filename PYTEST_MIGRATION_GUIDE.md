# Quick Migration Guide - Unittest → Pytest Style

## 🎯 Tại sao nên chuyển?

- ✅ **Code ngắn hơn 50%** - Ít boilerplate
- ✅ **Fixtures tái sử dụng** - DRY principle
- ✅ **Chạy nhanh hơn** - Scope management
- ✅ **Dễ đọc hơn** - assert thay vì assertEqual

## 📊 So sánh Cú pháp

### Assert Statements

```python
# ❌ Old unittest style
self.assertEqual(a, b)
self.assertTrue(condition)
self.assertIn(item, list)
self.assertRaises(Exception)

# ✅ New pytest style
assert a == b
assert condition
assert item in list
with pytest.raises(Exception):
    do_something()
```

### Test Structure

```python
# ❌ Old: Class-based with setUp
from django.test import TestCase

class MyModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.company = Company.objects.create(...)
    
    def test_something(self):
        self.assertEqual(self.user.email, 'test@test.com')

# ✅ New: Function-based with fixtures
import pytest

@pytest.mark.django_db
def test_something(user, company):
    assert user.email == 'test@test.com'
```

### API Tests

```python
# ❌ Old: APITestCase with force_authenticate
from rest_framework.test import APITestCase

class MyAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(...)
        self.client.force_authenticate(user=self.user)
    
    def test_api(self):
        response = self.client.get('/api/endpoint/')
        self.assertEqual(response.status_code, 200)

# ✅ New: Use authenticated_client fixture
import pytest
from rest_framework import status

@pytest.mark.django_db
def test_api(authenticated_client):
    response = authenticated_client.get('/api/endpoint/')
    assert response.status_code == status.HTTP_200_OK
```

## 🔄 Step-by-Step Migration

### Step 1: Xác định Test cần chuyển

```bash
# Tìm các file dùng TestCase
grep -r "class.*TestCase" apps/*/tests.py
```

### Step 2: Check Fixtures có sẵn

Mở `conftest.py` xem fixtures nào đã có:
- `candidate_user`
- `recruiter_user`
- `vip_recruiter_user`
- `company`
- `job`
- `api_client`
- `authenticated_client`
- `candidate_client`

### Step 3: Convert từng Test Class

**Ví dụ thực tế:**

```python
# ===== BEFORE (apps/companies/tests.py) =====
from django.test import TestCase
from rest_framework.test import APITestCase

class CompanyModelTest(TestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            description='A leading tech company',
            address='123 Test Street',
            owner=self.recruiter
        )
    
    def test_company_creation(self):
        self.assertEqual(self.company.name, 'Test Company')
        self.assertEqual(self.company.owner, self.recruiter)
    
    def test_company_str_representation(self):
        self.assertEqual(str(self.company), 'Test Company')

# ===== AFTER (apps/companies/test_pytest_style.py) =====
import pytest
from apps.companies.models import Company

@pytest.mark.django_db
def test_company_creation(recruiter_user):
    company = Company.objects.create(
        name='Test Company',
        description='A leading tech company',
        address='123 Test Street',
        owner=recruiter_user
    )
    
    assert company.name == 'Test Company'
    assert company.owner == recruiter_user
    assert str(company) == 'Test Company'
```

**Kết quả**: 20 dòng → 10 dòng (50% shorter!)

### Step 4: Convert API Tests

```python
# ===== BEFORE =====
class CompanyAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.recruiter = User.objects.create_user(...)
        self.company = Company.objects.create(...)
        self.client.force_authenticate(user=self.recruiter)
    
    def test_update_company(self):
        url = reverse('company-detail', args=[self.company.id])
        data = {'description': 'Updated'}
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.description, 'Updated')

# ===== AFTER =====
@pytest.mark.django_db
def test_update_company(authenticated_client, company):
    url = reverse('company-detail', args=[company.id])
    data = {'description': 'Updated'}
    response = authenticated_client.patch(url, data)
    
    assert response.status_code == 200
    company.refresh_from_db()
    assert company.description == 'Updated'
```

## 🎨 Advanced Patterns

### Parametrized Tests

```python
# ❌ Old: Write multiple similar tests
def test_employee_count_1_10(self):
    company = Company.objects.create(..., employee_count='1-10')
    self.assertTrue(company.employee_count == '1-10')

def test_employee_count_10_50(self):
    company = Company.objects.create(..., employee_count='10-50')
    self.assertTrue(company.employee_count == '10-50')

# ✅ New: Single parametrized test
@pytest.mark.django_db
@pytest.mark.parametrize("employee_count", [
    "1-10", "10-50", "50-100", "100-500", "500+"
])
def test_employee_count_options(recruiter_user, employee_count):
    company = Company.objects.create(
        name=f'Company {employee_count}',
        owner=recruiter_user,
        employee_count=employee_count
    )
    assert company.employee_count == employee_count
```

### Fixtures với Scope

```python
# Fixture chỉ tạo 1 lần cho cả session (nhanh hơn)
@pytest.fixture(scope='session')
def django_db_setup():
    # Setup database once
    pass

# Fixture tạo mỗi lần gọi (mặc định)
@pytest.fixture
def fresh_user(db):
    return User.objects.create_user(...)
```

### Nested Fixtures

```python
# Fixture phụ thuộc vào fixture khác
@pytest.fixture
def job(company):  # company fixture auto-called
    return Job.objects.create(
        title='Python Developer',
        company=company,  # Reuse company fixture
        ...
    )
```

## 📋 Checklist Migration

- [ ] Tạo file mới `test_pytest_style.py` (giữ file cũ để so sánh)
- [ ] Import pytest: `import pytest`
- [ ] Thêm decorator: `@pytest.mark.django_db`
- [ ] Chuyển `self.assertEqual()` → `assert`
- [ ] Xóa `setUp()`, dùng fixtures thay thế
- [ ] Chuyển `self.client` → `authenticated_client`
- [ ] Test lại: `pytest apps/myapp/test_pytest_style.py -v`
- [ ] So sánh coverage: `pytest --cov=apps.myapp`
- [ ] Nếu OK, xóa file cũ hoặc đổi tên

## 🛠️ Tools & Commands

### Chạy tests cụ thể

```bash
# Chạy 1 file
pytest apps/companies/test_pytest_style.py

# Chạy 1 function
pytest apps/companies/test_pytest_style.py::test_company_creation

# Chạy tests có tên chứa keyword
pytest -k "company"

# Chạy với verbose
pytest -v

# Chạy với coverage
pytest --cov=apps.companies apps/companies/test_pytest_style.py
```

### Debug tests

```bash
# Print output
pytest -s

# Stop at first failure
pytest -x

# Drop into debugger on failure
pytest --pdb
```

## ⚠️ Common Pitfalls

### 1. Quên @pytest.mark.django_db

```python
# ❌ Lỗi: no such table
def test_user():
    user = User.objects.create(...)  # ERROR!

# ✅ OK
@pytest.mark.django_db
def test_user():
    user = User.objects.create(...)
```

### 2. Dùng self trong pytest function

```python
# ❌ Sai: pytest functions không có self
@pytest.mark.django_db
def test_something(user):
    self.assertEqual(user.email, 'test@test.com')  # ERROR!

# ✅ Đúng
@pytest.mark.django_db
def test_something(user):
    assert user.email == 'test@test.com'
```

### 3. Fixture name không khớp

```python
# conftest.py có fixture tên "recruiter_user"

# ❌ Sai
def test_something(recruiter):  # Tên không khớp!
    pass

# ✅ Đúng
def test_something(recruiter_user):  # Khớp tên fixture
    pass
```

## 📚 Example: Complete Migration

Xem file: `apps/companies/test_pytest_style.py`

Đây là ví dụ hoàn chỉnh đã migrate từ unittest sang pytest style.

## 🎯 Khi nào nên migrate?

**Nên migrate:**
- ✅ Tests có nhiều code lặp trong setUp()
- ✅ Tests chạy chậm (do tạo dữ liệu nhiều lần)
- ✅ Muốn viết code gọn hơn
- ✅ Cần parametrized tests

**Chưa cần migrate:**
- ⏸️ Tests đơn giản, không có setup phức tạp
- ⏸️ Tests đang chạy ổn và ít khi sửa
- ⏸️ Team chưa quen pytest

## 🎉 Kết luận

Migration từ unittest sang pytest:
- Giảm 50% code
- Tăng 2x tốc độ
- Dễ maintain hơn
- Modern & powerful

**Bắt đầu với 1 file nhỏ để làm quen!**

---

Tham khảo:
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- Example: `apps/companies/test_pytest_style.py`
