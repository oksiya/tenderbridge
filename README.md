# TenderBridge API 🌉

A secure, blockchain-integrated tender management system with role-based access control.

## 🎯 Overview

TenderBridge provides a comprehensive platform for managing public procurement tenders with blockchain-backed transparency and accountability. Awards are permanently recorded on Ethereum blockchain for immutable audit trails.

## ✨ Features

### Core Functionality
- 📝 **Tender Management** - Create, publish, and manage tenders
- 💼 **Bid Submission** - Companies submit competitive bids
- 🏆 **Award System** - Award tenders with blockchain verification
- 🔗 **Blockchain Integration** - Immutable award records on Ethereum
- 👥 **Company Management** - Multi-user company accounts

### Security & Access Control (Phase 1) ✅
- 🔐 **Role-Based Access Control** - 5 hierarchical user roles
- ✉️ **Email Verification** - Secure email confirmation system
- 🔑 **Password Reset** - Secure password recovery flow
- 🛡️ **Authorization** - Fine-grained permission controls
- 🗑️ **Safe Deletion** - Soft delete with cascade protection

### User Roles
- **Admin** (100) - Full system access
- **Company Admin** (80) - Manage company users and settings
- **Tender Manager** (60) - Create tenders and award decisions
- **Evaluator** (40) - Score and evaluate bids (future)
- **User** (20) - Basic bidding capabilities

## 🚀 Quick Start

### Prerequisites
- Podman or Docker
- PostgreSQL 15
- Redis 7
- Ganache (Ethereum development blockchain)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/oksiya/tenderbridge.git
   cd tenderbridge
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Deploy and start services**
   ```bash
   ./deploy_and_start.sh
   ```

4. **Apply Phase 1 migration**
   ```bash
   podman exec -it tenderbridge_db_1 psql -U tenderuser -d tenderbridge < migrations/phase1_security.sql
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Redoc: http://localhost:8000/redoc

## 📚 Documentation

- **[Phase 1 Implementation](PHASE1_IMPLEMENTATION.md)** - Complete Phase 1 documentation
- **[Phase 1 Quick Start](PHASE1_QUICKSTART.md)** - Quick reference guide
- **[Phase 1 Test Results](PHASE1_TEST_RESULTS.md)** - Testing verification
- **[Deployment Guide](archive/DEPLOYMENT.md)** - Production deployment

## 🔧 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login with credentials
- `POST /auth/verify-email` - Verify email address
- `POST /auth/resend-verification` - Resend verification email
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token

### Users
- `GET /users/me` - Get current user info
- `GET /users/` - List users (admin/company_admin)
- `GET /users/{id}` - Get user details
- `PUT /users/{id}/role` - Update user role

### Companies
- `POST /company/` - Create company
- `GET /company/` - List active companies
- `GET /company/{id}` - Get company details
- `PUT /company/{id}` - Update company
- `DELETE /company/{id}` - Deactivate company (soft delete)
- `POST /company/assign` - Assign user to company
- `GET /company/{id}/users` - List company users

### Tenders
- `POST /tenders/` - Create tender (tender_manager+)
- `POST /tenders/upload` - Create tender with document
- `GET /tenders/` - List all tenders
- `GET /tenders/{id}` - Get tender details
- `PUT /tenders/{id}/close` - Close tender
- `POST /tenders/{id}/award` - Award tender (blockchain)
- `GET /tenders/{id}/verify` - Verify award on blockchain

### Bids
- `POST /bids/upload` - Submit bid with document
- `GET /bids/company/{id}` - List company bids (authorized)
- `GET /bids/tender/{id}` - List tender bids (tender owner)
- `GET /bids/{id}` - Get bid details
- `PUT /bids/{id}/status` - Update bid status (tender owner)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TenderBridge API                     │
│                     (FastAPI)                           │
├─────────────────────────────────────────────────────────┤
│  Auth  │  Users  │  Companies  │  Tenders  │  Bids    │
└────┬────────────────────────────────────────────────┬───┘
     │                                                 │
     ├──────────────┬──────────────┬─────────────────┤
     ▼              ▼              ▼                  ▼
┌─────────┐   ┌──────────┐   ┌─────────┐      ┌──────────┐
│PostgreSQL│   │  Redis   │   │ Ganache │      │ Worker   │
│   DB    │   │  Queue   │   │Ethereum │      │   (RQ)   │
└─────────┘   └──────────┘   └─────────┘      └──────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │  Smart Contract  │
                          │ TenderAwardRegistry│
                          └──────────────────┘
```

## 🔐 Security Features

### Phase 1 (Implemented) ✅
- ✅ Role-based access control
- ✅ Email verification system
- ✅ Password reset flow
- ✅ Authorization on sensitive operations
- ✅ Soft delete with cascade checks
- ✅ Secure token generation
- ✅ Company membership validation
- ✅ Self-bid prevention

### Future Enhancements
- [ ] Multi-factor authentication (2FA)
- [ ] Rate limiting
- [ ] Audit logging
- [ ] Email service integration
- [ ] Session management
- [ ] IP-based access control

## 🧪 Testing

### Run Tests
```bash
# Test user registration and verification
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Test /users/me endpoint
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

See [PHASE1_QUICKSTART.md](PHASE1_QUICKSTART.md) for complete testing guide.

## 🛣️ Roadmap

### Phase 1: Critical Security Fixes ✅ COMPLETE
- [x] Authorization on bid viewing
- [x] Safe company deletion
- [x] Secured user assignment
- [x] Email verification
- [x] Password reset
- [x] Role-based access control

### Phase 2: Tender Workflow (Next)
- [ ] Tender state machine (draft → published → awarded)
- [ ] Bid withdrawal and revision
- [ ] Award justification requirement
- [ ] Notification system
- [ ] Email integration

### Phase 3: Evaluation System
- [ ] Evaluation criteria definition
- [ ] Bid scoring interface
- [ ] Multi-evaluator support
- [ ] Score calculation and ranking
- [ ] Evaluation reports

### Phase 4: Advanced Features
- [ ] Q&A system for clarifications
- [ ] Multi-file uploads
- [ ] Document version control
- [ ] Audit trail
- [ ] Analytics dashboard

### Phase 5: Compliance & Reporting
- [ ] BEE integration
- [ ] Compliance reports
- [ ] Export capabilities
- [ ] Advanced filtering/search

## 📦 Technology Stack

- **Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL 15
- **ORM:** SQLAlchemy 2.0
- **Queue:** Redis + RQ
- **Blockchain:** Web3.py 6.20.1 + Ganache v7.9.1
- **Smart Contracts:** Solidity 0.8.0
- **Authentication:** JWT (python-jose)
- **Password Hashing:** Bcrypt
- **Containerization:** Podman/Docker

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

**Oksiya**
- GitHub: [@oksiya](https://github.com/oksiya)

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Web3.py for Ethereum integration
- Ganache for local blockchain development
- SQLAlchemy for robust ORM capabilities

## 📞 Support

For issues and questions:
1. Check the documentation in `/docs`
2. Review [PHASE1_IMPLEMENTATION.md](PHASE1_IMPLEMENTATION.md)
3. Check existing issues on GitHub
4. Create a new issue with detailed description

---

**Status:** Phase 1 Complete ✅ | Ready for Phase 2 🚀
**Last Updated:** October 14, 2025
