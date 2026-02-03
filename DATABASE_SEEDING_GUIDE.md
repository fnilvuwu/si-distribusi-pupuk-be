# Database Seeding and Testing Guide

## Overview

This document describes the comprehensive database seeding script and test suite for the SI Distribusi Pupuk (Free Fertilizer Distribution System) application.

## What's Been Added

### 1. Comprehensive Dummy Data Seeding (`db/seed_all_data.py`)

A complete seeding script that populates the database with realistic test data across all entities:

#### Data Seeded:
- **Users (9 total):**
  - 5 Petani (Farmers)
  - 2 Distributors
  - 1 Admin
  - 1 Superadmin

- **Fertilizer Types (6):**
  - Urea (5000 kg)
  - TSP - Triple Super Phosphate (3000 kg)
  - KCl - Potassium Chloride (2500 kg)
  - NPK 16:16:16 (4000 kg)
  - Pupuk Organik Kompos (6000 kg)
  - Dolomit (2000 kg)

- **Fertilizer Requests (6):**
  - Various status stages: pending, terverifikasi, dijadwalkan, dikirim, selesai
  - Real-world scenarios with different approval amounts

- **Distribution Schedules (5):**
  - Linked to requests with different delivery dates
  - Status tracking: dijadwalkan, dikirim

- **Stock History (4 records):**
  - Track stock additions and reductions
  - Associated with admin user

- **Harvest Records (6):**
  - Multiple crops: Padi, Jagung, Cabai, Bawang Merah, Tomat, Kentang
  - Historical dates for realistic data

- **Distribution Events (2):**
  - Event-based distribution schedules
  - 4 event items across 2 events

- **Verification Records (2):**
  - Receipt verification by distributors
  - Photo evidence URLs

### 2. Comprehensive Test Suite (`tests/test_database.py`)

30 unit and integration tests covering all database entities:

#### Test Coverage:

**User Tests:**
- User creation
- Username uniqueness constraint
- Role validation

**Petani Profile Tests:**
- Profile creation
- NIK uniqueness
- Verification status handling
- Profile-request relationships

**Fertilizer Tests:**
- Fertilizer creation
- Fertilizer name uniqueness
- Stock updates
- Multiple fertilizers management

**Request Tests:**
- Request creation
- Status value validation
- Status progression workflow
- Request relationships with petani and pupuk

**Distribution Schedule Tests:**
- Schedule creation
- Status validation
- Date tracking

**Harvest Tests:**
- Harvest record creation
- Multiple crops per petani

**Stock History Tests:**
- Stock increase recording
- Stock decrease recording
- Historical timeline tracking

**Event Tests:**
- Event creation
- Events with multiple items
- Relationship management

**Verification Tests:**
- Verification record creation
- Verification relationships

**Integration Tests:**
- Complete request workflow (pending → selesai)
- Stock tracking through operations
- Data count verification

## How to Use

### 1. Seed the Database

Run the seeding script to populate your database with dummy data:

```bash
python db/seed_all_data.py
```

**Output:**
```
Clearing existing test data...
[OK] Cleared existing data

Seeding users and profiles...
[OK] Seeded 5 petani, 2 distributor, 1 admin, 1 superadmin

Seeding fertilizers...
[OK] Seeded 6 types of fertilizers

... (more seeding messages)

DATABASE SEEDING COMPLETED SUCCESSFULLY
============================================================
[OK] Users created: 9
[OK] Fertilizer types: 6
[OK] Requests: 6
[OK] Distribution schedules: 5
[OK] Stock history: 4
[OK] Harvest records: 6
[OK] Events: 2
[OK] Verification records: 2
============================================================
```

### 2. Run the Tests

Execute the comprehensive test suite:

```bash
pytest tests/test_database.py -v
```

**Expected Output:**
```
============================= test session starts =============================
collected 30 items

tests/test_database.py::TestUserEntity::test_user_creation PASSED        [  3%]
tests/test_database.py::TestUserEntity::test_user_unique_username PASSED  [  6%]
tests/test_database.py::TestUserEntity::test_user_role_validation PASSED  [10%]
... (28 more tests)

============================= 30 passed in 27.70s ==============================
```

## Test Categories

### Unit Tests
Individual entity tests that verify model behavior:
- Creation and validation
- Constraint enforcement
- Relationship loading

### Integration Tests
End-to-end workflow tests:
- Complete request processing from pending to completion
- Stock tracking through operations
- Multi-step workflows

## Database Schema Tested

All the following database tables are tested:

1. **users** - User accounts with roles
2. **profile_petani** - Farmer profiles
3. **profile_distributor** - Distributor profiles
4. **profile_admin** - Admin profiles
5. **profile_superadmin** - Superadmin profiles
6. **stok_pupuk** - Fertilizer inventory
7. **pengajuan_pupuk** - Fertilizer requests
8. **jadwal_distribusi_pupuk** - Distribution schedules
9. **hasil_tani** - Harvest records
10. **riwayat_stock_pupuk** - Stock change history
11. **jadwal_distribusi_event** - Distribution events
12. **jadwal_distribusi_item** - Event items
13. **verifikasi_penerima_pupuk** - Receipt verification

## Key Features

✓ **Comprehensive Coverage**: Tests all entity creation, constraints, and relationships
✓ **Realistic Data**: Dummy data reflects real-world scenarios
✓ **Status Workflows**: Tests complete status progression from request to completion
✓ **Historical Data**: Stock history, harvest dates, and timelines
✓ **Relationship Testing**: Validates foreign key relationships
✓ **Constraint Validation**: Tests unique constraints and check constraints
✓ **Integration Scenarios**: Full end-to-end workflow tests

## Default Test Users

You can use these credentials for testing (passwords: password123):

- **Petani**: petani001, petani002, petani003, petani004, petani005
- **Distributor**: distributor001, distributor002
- **Admin**: admin001
- **Superadmin**: superadmin001

## Notes

- The seed script clears existing test data before seeding (if any)
- Tests use an in-memory SQLite database for isolation
- Database changes are not persisted between test runs
- All timestamps use server time for consistency
- Stock quantities match realistic agricultural scenarios

## Next Steps

1. Verify data by running: `python db/seed_all_data.py`
2. Run tests: `pytest tests/test_database.py -v`
3. Start the API server and test with the seeded data
4. Extend tests as needed for API endpoints

---

**Created**: January 25, 2026
**Test Status**: All 30 tests PASSING
**Data Status**: Successfully seeded with comprehensive test data
