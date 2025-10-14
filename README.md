# TenderBridge API 🌉

A secure, blockchain-integrated tender management system with role-based access control.

## 🎯 Overview

TenderBridge provides a comprehensive platform for managing public procurement tenders with blockchain-backed transparency and accountability. Awards are permanently recorded on Ethereum blockchain for immutable audit trails.

## ✨ Features

### Core Functionality
- 📝 **Tender Management** - Create, publish, and manage tenders with workflow
- 💼 **Bid Submission** - Companies submit, revise, and withdraw bids
- 🏆 **Award System** - Award tenders with mandatory justification and blockchain verification
- 🔗 **Blockchain Integration** - Immutable award records on Ethereum
- 👥 **Company Management** - Multi-user company accounts
- 🔔 **Notifications** - Real-time in-app notifications for all events

### Security & Access Control (Phase 1) ✅
- 🔐 **Role-Based Access Control** - 5 hierarchical user roles
- ✉️ **Email Verification** - Secure email confirmation system
- 🔑 **Password Reset** - Secure password recovery flow
- 🛡️ **Authorization** - Fine-grained permission controls
- 🗑️ **Safe Deletion** - Soft delete with cascade protection

### Workflow Enhancements (Phase 2) ✅
- 🔄 **Tender State Machine** - 7-state lifecycle with transition validation
  - draft → published → open → evaluation → awarded
  - Cancellation with reason tracking
  - Terminal state protection
- ✏️ **Bid Revision** - Update bids before deadline with full version history
- 🚫 **Bid Withdrawal** - Withdraw bids with reason tracking
- ⚖️ **Award Justification** - Mandatory transparency for award decisions
- 🔔 **Notification System** - In-app notifications for all events
- 🤖 **Automatic Updates** - Auto-update bid statuses on award

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
- `POST /tenders/` - Create tender (tender_manager+, starts in 'draft')
- `POST /tenders/upload` - Create tender with document
- `GET /tenders/` - List all tenders
- `GET /tenders/{id}` - Get tender details
- `PUT /tenders/{id}` - Update tender (draft/published only) **[Phase 2]**
- `PUT /tenders/{id}/status` - Transition tender status **[Phase 2]**
- `PUT /tenders/{id}/close` - Close tender
- `POST /tenders/{id}/award` - Award tender with justification (blockchain)
- `GET /tenders/{id}/verify` - Verify award on blockchain

### Bids
- `POST /bids/upload` - Submit bid with document
- `GET /bids/company/{id}` - List company bids (authorized)
- `GET /bids/tender/{id}` - List tender bids (tender owner)
- `GET /bids/{id}` - Get bid details
- `PUT /bids/{id}/status` - Update bid status (tender owner)
- `PUT /bids/{id}/revise` - Revise bid (new amount/document) **[Phase 2]**
- `POST /bids/{id}/withdraw` - Withdraw bid with reason **[Phase 2]**

### Notifications **[Phase 2]**
- `GET /notifications/` - List user notifications
- `GET /notifications/unread/count` - Get unread count
- `POST /notifications/mark-read` - Mark specific as read
- `POST /notifications/mark-all-read` - Mark all as read
- `GET /notifications/{id}` - Get notification (auto-marks read)

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
- ✅ State machine transition validation **[Phase 2]**
- ✅ Audit trail tracking (timestamps, reasons, justifications) **[Phase 2]**

### Tender Workflow States **[Phase 2]**
```
draft → published → open → evaluation → awarded
                            ↘ closed ↗      ↘ cancelled
```

**State Rules:**
- **draft** - Can be edited, not visible to bidders
- **published** - Can be edited, visible to bidders (not yet accepting bids)
- **open** - Accepting bid submissions (no more edits)
- **evaluation** - Closed for bids, under review
- **closed** - Alternative to evaluation
- **awarded** - Winner selected (terminal state)
- **cancelled** - Tender cancelled with reason (terminal state)

### Future Enhancements
- [ ] Multi-factor authentication (2FA)
- [ ] Rate limiting
- [ ] Audit logging
- [ ] Email service integration (notifications ready)
- [ ] Session management
- [ ] IP-based access control
- [ ] Scheduled tender closure (auto-close at deadline)
- [ ] Evaluation system with scoring
- [ ] Q&A system for bidder questions

## 🧪 Testing

### Run Tests
```bash
# Phase 1: Security and access control
# See PHASE1_QUICKSTART.md for complete guide

# Phase 2: Workflow enhancements
./test_phase2.sh

# Or test manually:
# 1. Create tender (starts in draft)
curl -X POST http://localhost:8000/tenders/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","description":"Test tender","closing_date":"2025-12-31T23:59:59"}'

# 2. Publish tender
curl -X PUT http://localhost:8000/tenders/TENDER_ID/status \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"published"}'

# 3. Open for bids
curl -X PUT http://localhost:8000/tenders/TENDER_ID/status \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"open"}'
```

**Testing Guides:**
- [PHASE1_QUICKSTART.md](PHASE1_QUICKSTART.md) - Security features
- [PHASE2_QUICKSTART.md](PHASE2_QUICKSTART.md) - Workflow features
- [PHASE2_TEST_RESULTS.md](PHASE2_TEST_RESULTS.md) - Test results

## 🛣️ Roadmap

### Phase 1: Critical Security Fixes ✅ COMPLETE
- [x] Authorization on bid viewing
- [x] Safe company deletion
- [x] Secured user assignment
- [x] Email verification
- [x] Password reset
- [x] Role-based access control

### Phase 2: Tender Workflow ✅ COMPLETE
- [x] Tender state machine (draft → published → open → evaluation → awarded)
- [x] Bid withdrawal with reason tracking
- [x] Bid revision with version history
- [x] Award justification requirement (mandatory)
- [x] Notification system infrastructure
- [x] Automatic bid status updates on award

### Phase 2.1: Notification Integration (Quick Win)
- [ ] Add notification hooks to tender status changes
- [ ] Add notification hooks to bid actions
- [ ] Add notification hooks to award process
- [ ] Enhanced error messages
- [ ] API documentation updates

### Phase 3: Advanced Features
- [ ] **Email Integration** - Connect notifications to email service
- [ ] **Scheduled Jobs** - Auto-close tenders at deadline
- [ ] **Evaluation System** - Scoring and multi-evaluator support
- [ ] **Q&A System** - Bidder questions and public responses
- [ ] **Document Management** - Multiple files, versioning, preview
- [ ] **Reporting** - Tender analytics and audit reports

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
