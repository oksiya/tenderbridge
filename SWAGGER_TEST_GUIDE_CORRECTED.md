# Swagger UI Manual Testing Guide - CORRECTED

**Date:** October 15, 2025  
**Purpose:** Step-by-step manual testing of all endpoints with correct data structures

---

## Prerequisites

### 1. Access Swagger UI
```
http://localhost:8000/docs
```

### 2. Truncate All Tables (Fresh Start)
```bash
# Truncate tables (in order to respect foreign keys)
podman exec -it tenderbridge_db_1 psql -U tenderuser -d tenderbridge -c "
TRUNCATE TABLE answers, questions, documents, bids, tenders, notifications, companies, users, email_logs RESTART IDENTITY CASCADE;"

# Exit
\q
```

---

## Testing Workflow

### Phase 1: Initial Setup (Database + First Admin)

> **IMPORTANT:** Create the first admin user directly in the database since there's no super-admin endpoint.

#### 1.1 Create First Admin User in Database
```bash
# Connect to database
podman exec -it tenderbridge_db_1 psql -U tenderuser -d tenderbridge

# Create admin user with pre-hashed password
INSERT INTO users (id, email, password_hash, role, is_verified, created_at) 
VALUES (
  gen_random_uuid(),
  'admin@system.com',
  '$2b$12$9TJVsFbk6K1kDoyrP6cv9e2G6xOzyQpytgWQcaE.kPLLbyqEocc.W',
  'admin',
  'true',
  NOW()
);

# Verify admin was created
SELECT id, email, role, is_verified FROM users;

# Exit
\q
```

**Password:** `admin` (pre-hashed in the SQL above)

---

### Phase 2: Login and Setup Companies

#### 2.1 Login as Admin
**Endpoint:** `POST /auth/login`

```json
{
  "email": "admin@system.com",
  "password": "admin"
}
```

**Expected:** Returns `access_token`  
**Action:** 
1. Copy the `access_token` from response
2. Click the **Authorize** button (🔒) at top of Swagger UI
3. Paste the token (no "Bearer" prefix needed)
4. Click "Authorize" then "Close"

#### 2.2 Create Company: ACME Corporation
**Endpoint:** `POST /company/`

```json
{
  "name": "ACME Corporation",
  "registration_number": "REG-ACME-2025",
  "bee_level": 3
}
```

**Expected:** Company created  
**Action:** Copy the `id` from response → Save as **company_1_id**

#### 2.3 Create Company: Government Agency
**Endpoint:** `POST /company/`

```json
{
  "name": "Government Procurement Agency",
  "registration_number": "GOV-AGENCY-2025"
}
```

**Expected:** Company created  
**Action:** Copy the `id` → Save as **company_2_id**

#### 2.4 Create Company: Tech Solutions
**Endpoint:** `POST /company/`

```json
{
  "name": "Tech Solutions Inc",
  "registration_number": "REG-TECH-2025",
  "bee_level": 4
}
```

**Expected:** Company created  
**Action:** Copy the `id` → Save as **company_3_id**

---

### Phase 3: Register Users via API

#### 3.1 Register ACME Admin
**Endpoint:** `POST /auth/register`

```json
{
  "email": "john@acmecorp.com",
  "password": "SecurePass123!"
}
```

**Expected:** User registered with role="user" (default)  
**Note:** We'll assign company and update role next

#### 3.2 Register Government User
**Endpoint:** `POST /auth/register`

```json
{
  "email": "procurement@govagency.gov",
  "password": "GovSecure456!"
}
```

**Expected:** User registered

#### 3.3 Register Bidder User
**Endpoint:** `POST /auth/register`

```json
{
  "email": "sales@techsolutions.com",
  "password": "BidPass789!"
}
```

**Expected:** User registered

#### 3.4 Get All Users (to get UUIDs)
**Endpoint:** `GET /users/`

**Expected:** List of 4 users  
**Action:** Copy each user's `id`:
- admin@system.com → **admin_user_id**
- john@acmecorp.com → **acme_user_id**
- procurement@govagency.gov → **gov_user_id**
- sales@techsolutions.com → **tech_user_id**

---

### Phase 4: Assign Users to Companies

#### 4.1 Assign John to ACME
**Endpoint:** `POST /company/assign`

```json
{
  "user_id": "PASTE_acme_user_id_HERE",
  "company_id": "PASTE_company_1_id_HERE"
}
```

**Expected:** "User john@acmecorp.com successfully linked to ACME Corporation"

#### 4.2 Assign Procurement to Government
**Endpoint:** `POST /company/assign`

```json
{
  "user_id": "PASTE_gov_user_id_HERE",
  "company_id": "PASTE_company_2_id_HERE"
}
```

**Expected:** User linked

#### 4.3 Assign Sales to Tech Solutions
**Endpoint:** `POST /company/assign`

```json
{
  "user_id": "PASTE_tech_user_id_HERE",
  "company_id": "PASTE_company_3_id_HERE"
}
```

**Expected:** User linked

---

### Phase 5: Update User Roles

#### 5.1 Set John as Company Admin
**Endpoint:** `PUT /users/{user_id}/role`  
**Path Parameter:** PASTE **acme_user_id**

```json
{
  "role": "company_admin"
}
```

**Expected:** Role updated to "company_admin"

#### 5.2 Set Procurement as Contracting Authority
**Endpoint:** `PUT /users/{user_id}/role`  
**Path Parameter:** PASTE **gov_user_id**

```json
{
  "role": "contracting_authority"
}
```

**Expected:** Role updated

#### 5.3 Set Sales as Bidder
**Endpoint:** `PUT /users/{user_id}/role`  
**Path Parameter:** PASTE **tech_user_id**

```json
{
  "role": "bidder"
}
```

**Expected:** Role updated

---

### Phase 6: Tender Management (As Authority)

#### 6.1 Login as Government User
**Endpoint:** `POST /auth/login`

```json
{
  "email": "procurement@govagency.gov",
  "password": "GovSecure456!"
}
```

**Expected:** Returns new token  
**Action:** Click Authorize (🔒) and replace with NEW token

#### 6.2 Create First Tender
**Endpoint:** `POST /tenders/`

```json
{
  "title": "IT Infrastructure Upgrade Project",
  "description": "Complete upgrade of government IT infrastructure including servers, networking equipment, and cloud migration services. The project involves modernizing legacy systems and implementing cybersecurity measures.",
  "budget": 500000.00,
  "deadline": "2025-11-30T17:00:00Z",
  "requirements": "- Minimum 5 years experience in enterprise IT\n- ISO 27001 certification required\n- References from at least 3 government projects\n- 24/7 support availability\n- Migration plan with zero downtime guarantee",
  "category": "IT Services",
  "submission_deadline": "2025-11-15T17:00:00Z"
}
```

**Expected:** Tender created with status="draft"  
**Action:** Copy the `id` → Save as **tender_1_id**

#### 6.3 Create Second Tender
**Endpoint:** `POST /tenders/`

```json
{
  "title": "Office Supplies Annual Contract",
  "description": "Annual supply contract for office materials, stationery, and consumables for all government offices. Expected volume: 50 offices, 1000+ employees.",
  "budget": 75000.00,
  "deadline": "2025-12-31T17:00:00Z",
  "requirements": "- Proven track record in B2B supplies\n- Next-day delivery capability\n- Quality certifications\n- Bulk pricing with volume discounts\n- Online ordering system",
  "category": "Supplies",
  "submission_deadline": "2025-11-20T17:00:00Z"
}
```

**Expected:** Second tender created  
**Action:** Copy the `id` → Save as **tender_2_id**

#### 6.4 Get All Tenders (Test Pagination & Caching)
**Endpoint:** `GET /tenders/`

**Parameters:**
- `skip`: 0
- `limit`: 10

**Expected:** Paginated response with 2 tenders
```json
{
  "items": [...],
  "total": 2,
  "skip": 0,
  "limit": 10,
  "has_more": false
}
```

**Test Caching:** Call this endpoint again immediately - second call should be faster!

#### 6.5 Get Tender Details
**Endpoint:** `GET /tenders/{tender_id}`  
**Path Parameter:** PASTE **tender_1_id**

**Expected:** Full tender details returned

#### 6.6 Update Tender
**Endpoint:** `PUT /tenders/{tender_id}`  
**Path Parameter:** PASTE **tender_1_id**

```json
{
  "title": "IT Infrastructure Upgrade Project - UPDATED",
  "description": "Complete upgrade of government IT infrastructure including servers, networking equipment, and cloud migration services. The project involves modernizing legacy systems and implementing cybersecurity measures.\n\n**UPDATE:** Added requirement for quantum-ready encryption.",
  "budget": 550000.00,
  "deadline": "2025-11-30T17:00:00Z",
  "requirements": "- Minimum 5 years experience in enterprise IT\n- ISO 27001 certification required\n- References from at least 3 government projects\n- 24/7 support availability\n- Migration plan with zero downtime guarantee\n- Quantum-ready encryption implementation",
  "category": "IT Services",
  "submission_deadline": "2025-11-15T17:00:00Z"
}
```

**Expected:** Tender updated, cache invalidated

#### 6.7 Publish First Tender
**Endpoint:** `PUT /tenders/{tender_id}/status`  
**Path Parameter:** PASTE **tender_1_id**

```json
{
  "status": "published"
}
```

**Expected:** Status changed to "published"

#### 6.8 Publish Second Tender
**Endpoint:** `PUT /tenders/{tender_id}/status`  
**Path Parameter:** PASTE **tender_2_id**

```json
{
  "status": "published"
}
```

**Expected:** Second tender published

---

### Phase 7: Document Management

#### 7.1 Upload Tender Document
**Endpoint:** `POST /tenders/{tender_id}/upload`  
**Path Parameter:** PASTE **tender_1_id**

**Form Data:**
- `file`: Choose a PDF file
- `document_type`: requirements
- `description`: Detailed technical specifications and requirements

**Expected:** Document uploaded  
**Action:** Copy the `id` → Save as **doc_1_id**

#### 7.2 Upload Another Document
**Endpoint:** `POST /tenders/{tender_id}/upload`  
**Path Parameter:** PASTE **tender_1_id**

**Form Data:**
- `file`: Choose another file
- `document_type`: other
- `description`: Reference architecture diagrams

**Expected:** Second document uploaded

#### 7.3 List Tender Documents
**Endpoint:** `GET /documents/tender/{tender_id}`  
**Path Parameter:** PASTE **tender_1_id**

**Expected:** List of 2 documents

#### 7.4 Download Document
**Endpoint:** `GET /documents/{document_id}/download`  
**Path Parameter:** PASTE **doc_1_id**

**Expected:** File download

---

### Phase 8: Bidding Process

#### 8.1 Login as First Bidder (Tech Solutions)
**Endpoint:** `POST /auth/login`

```json
{
  "email": "sales@techsolutions.com",
  "password": "BidPass789!"
}
```

**Expected:** Returns token  
**Action:** Click Authorize (🔒) and use NEW token

#### 8.2 Create Bid
**Endpoint:** `POST /bids/`

```json
{
  "tender_id": "PASTE_tender_1_id_HERE",
  "amount": 485000.00,
  "proposal": "# Tech Solutions Inc - IT Infrastructure Proposal\n\n## Executive Summary\nTech Solutions Inc is pleased to submit our comprehensive proposal for the IT Infrastructure Upgrade Project. With over 8 years of experience in enterprise IT and successful completion of 15+ government projects, we are uniquely positioned to deliver this critical initiative.\n\n## Our Approach\n1. **Assessment Phase** (Weeks 1-2)\n   - Complete infrastructure audit\n   - Risk assessment\n   - Migration planning\n\n2. **Implementation Phase** (Weeks 3-12)\n   - Phased rollout to ensure zero downtime\n   - Parallel running of old and new systems\n   - Daily progress reports\n\n3. **Testing & Optimization** (Weeks 13-14)\n   - Comprehensive testing\n   - Performance optimization\n   - Security audits\n\n4. **Training & Handover** (Weeks 15-16)\n   - Staff training programs\n   - Documentation delivery\n   - 90-day support period\n\n## Cost Breakdown\n- Hardware & Software: $285,000\n- Implementation Services: $120,000\n- Training & Documentation: $35,000\n- Support & Maintenance (Year 1): $45,000\n\n**Total: $485,000**\n\n## Certifications\n- ISO 27001:2013\n- ISO 9001:2015\n- CMMI Level 3\n- Government Approved Vendor (GAV-2024)\n\n## Timeline\nProject completion: 16 weeks from contract signing\n\n## Guarantee\nZero-downtime migration guarantee backed by performance bonds.",
  "delivery_time": 112
}
```

**Expected:** Bid created  
**Action:** Copy the `id` → Save as **bid_1_id**

#### 8.3 Upload Bid Proposal Document
**Endpoint:** `POST /bids/{bid_id}/upload`  
**Path Parameter:** PASTE **bid_1_id**

**Form Data:**
- `file`: Upload a file
- `document_type`: proposal
- `description`: Detailed technical proposal and implementation plan

**Expected:** Document attached to bid

#### 8.4 Login as Second Bidder (ACME)
**Endpoint:** `POST /auth/login`

```json
{
  "email": "john@acmecorp.com",
  "password": "SecurePass123!"
}
```

**Expected:** Returns token  
**Action:** Authorize with NEW token

#### 8.5 Create Competing Bid
**Endpoint:** `POST /bids/`

```json
{
  "tender_id": "PASTE_tender_1_id_HERE",
  "amount": 520000.00,
  "proposal": "# ACME Corporation - Infrastructure Modernization Proposal\n\n## Company Overview\nACME Corporation brings 12 years of experience in large-scale IT infrastructure projects, specializing in government and enterprise clients.\n\n## Our Solution\nWe propose a cutting-edge, cloud-first architecture leveraging:\n- Multi-cloud strategy (AWS + Azure)\n- Kubernetes orchestration\n- Zero-trust security model\n- AI-powered monitoring\n\n## Project Phases\n### Phase 1: Discovery & Planning (3 weeks)\n- Infrastructure assessment\n- Cloud readiness evaluation\n- Security audit\n- Custom migration strategy\n\n### Phase 2: Cloud Foundation (4 weeks)\n- Cloud infrastructure setup\n- Network configuration\n- Security implementation\n- Compliance verification\n\n### Phase 3: Migration (8 weeks)\n- Phased application migration\n- Data migration with validation\n- Legacy system decommissioning\n- Performance optimization\n\n### Phase 4: Stabilization (3 weeks)\n- Monitoring implementation\n- Performance tuning\n- Staff training\n- Documentation\n\n## Investment Breakdown\n- Cloud Infrastructure (3-year): $180,000\n- Migration Services: $215,000\n- Security & Compliance: $75,000\n- Training & Support: $50,000\n\n**Total: $520,000**\n\n## Value Proposition\n- 40% reduction in operational costs\n- 99.99% uptime SLA\n- Quantum-ready encryption\n- 24/7/365 support\n- Industry-leading certifications\n\n## Guarantees\n- Performance bond covering full project value\n- Zero-downtime migration guarantee\n- 12-month warranty period\n- Fixed price commitment",
  "delivery_time": 126
}
```

**Expected:** Second bid created  
**Action:** Copy the `id` → Save as **bid_2_id**

---

### Phase 9: Q&A System

#### 9.1 Ask Question (as Tech Solutions Bidder)
**Login:** sales@techsolutions.com (if not already)

**Endpoint:** `POST /qa/questions`

```json
{
  "tender_id": "PASTE_tender_1_id_HERE",
  "question": "Regarding the quantum-ready encryption requirement: Could you please clarify the specific quantum algorithms and key sizes expected? Are you looking for post-quantum cryptography standards like CRYSTALS-Kyber or CRYSTALS-Dilithium?"
}
```

**Expected:** Question created with status="pending"  
**Action:** Copy the `id` → Save as **question_1_id**

#### 9.2 Ask Another Question
**Endpoint:** `POST /qa/questions`

```json
{
  "tender_id": "PASTE_tender_1_id_HERE",
  "question": "The requirements mention zero-downtime migration. Can you please confirm if this applies to all systems including the mainframe applications, or only the newer distributed systems? Also, what is the acceptable service degradation threshold during migration?"
}
```

**Expected:** Second question created  
**Action:** Copy the `id` → Save as **question_2_id**

#### 9.3 Login as Authority
**Endpoint:** `POST /auth/login`

```json
{
  "email": "procurement@govagency.gov",
  "password": "GovSecure456!"
}
```

**Expected:** Returns token  
**Action:** Authorize with NEW token

#### 9.4 List Questions for Tender
**Endpoint:** `GET /qa/tenders/{tender_id}/questions`  
**Path Parameter:** PASTE **tender_1_id**

**Expected:** List of 2 pending questions

#### 9.5 Answer First Question
**Endpoint:** `POST /qa/questions/{question_id}/answer`  
**Path Parameter:** PASTE **question_1_id**

```json
{
  "answer": "Thank you for your question. For the quantum-ready encryption requirement:\n\n1. We expect implementation of NIST-approved post-quantum cryptography algorithms, specifically:\n   - CRYSTALS-Kyber for key encapsulation (minimum security level 3)\n   - CRYSTALS-Dilithium for digital signatures (minimum security level 3)\n\n2. The solution should be compatible with FIPS 203 and FIPS 204 standards\n\n3. Hybrid approach is acceptable during transition period (combining classical and post-quantum algorithms)\n\n4. All encryption must support minimum 256-bit security level equivalent\n\nPlease ensure your proposal addresses crypto-agility to support future algorithm updates."
}
```

**Expected:** Question answered, status="answered"

#### 9.6 Answer Second Question
**Endpoint:** `POST /qa/questions/{question_id}/answer`  
**Path Parameter:** PASTE **question_2_id**

```json
{
  "answer": "Excellent question regarding zero-downtime requirements:\n\n1. **Scope**: Zero-downtime applies to:\n   - All web-based applications\n   - Email systems\n   - File servers\n   - Public-facing services\n\n2. **Mainframe applications**: We understand these may require brief maintenance windows. Acceptable approach:\n   - Maximum 2-hour downtime window per application\n   - Must be scheduled outside business hours (10 PM - 6 AM)\n   - Requires 2-week advance notice\n   - Maximum 3 such windows for entire project\n\n3. **Service degradation threshold**:\n   - Response time: No more than 20% increase during migration\n   - Availability: 99.9% minimum during migration period\n   - Transaction processing: No degradation in throughput\n\n4. **Monitoring**: Real-time monitoring required with automated rollback if thresholds exceeded\n\nPlease reflect this in your migration plan and provide specific mitigation strategies."
}
```

**Expected:** Question answered

---

### Phase 10: Notifications

#### 10.1 Get My Notifications
**Endpoint:** `GET /notifications/`

**Parameters:**
- `skip`: 0
- `limit`: 20

**Expected:** Paginated list of notifications (tender updates, bids, Q&A, etc.)

#### 10.2 Get Unread Count
**Endpoint:** `GET /notifications/unread-count`

**Expected:**
```json
{
  "count": 5
}
```

#### 10.3 Mark Notification as Read
**Endpoint:** `PUT /notifications/{notification_id}/read`  
**Path Parameter:** Use any notification `id` from the list

**Expected:** Notification marked as read

#### 10.4 Mark All as Read
**Endpoint:** `PUT /notifications/mark-all-read`

**Expected:** All notifications marked as read

---

### Phase 11: Award Process

#### 11.1 Login as Authority (if needed)
**Endpoint:** `POST /auth/login`

```json
{
  "email": "procurement@govagency.gov",
  "password": "GovSecure456!"
}
```

**Action:** Authorize with token

#### 11.2 List All Bids for Tender (Test Caching)
**Endpoint:** `GET /bids/tender/{tender_id}`  
**Path Parameter:** PASTE **tender_1_id**

**Expected:** List of 2 bids  
**Test:** Call twice - second should be cached/faster

#### 11.3 Get Bid Details
**Endpoint:** `GET /bids/{bid_id}`  
**Path Parameter:** PASTE **bid_1_id**

**Expected:** Full bid details with documents

#### 11.4 Update Bid Status to Under Review
**Endpoint:** `PUT /bids/{bid_id}/status`  
**Path Parameter:** PASTE **bid_1_id**

```json
{
  "status": "under_review"
}
```

**Expected:** Status updated

#### 11.5 Award Tender to Winning Bid
**Endpoint:** `POST /tenders/{tender_id}/award`  
**Path Parameter:** PASTE **tender_1_id**

```json
{
  "winning_bid_id": "PASTE_bid_1_id_HERE",
  "award_notes": "After careful evaluation of both proposals, the committee has decided to award this contract to Tech Solutions Inc based on the following criteria:\n\n**Technical Evaluation (40 points)**\n- Tech Solutions: 38/40\n- ACME Corporation: 35/40\n\n**Financial Evaluation (30 points)**\n- Tech Solutions: 28/30 (more competitive pricing)\n- ACME Corporation: 24/30\n\n**Experience & References (30 points)**\n- Tech Solutions: 27/30\n- ACME Corporation: 28/30\n\n**Total Scores:**\n- Tech Solutions Inc: 93/100 ✓ WINNER\n- ACME Corporation: 87/100\n\n**Key Decision Factors:**\n1. Superior cost-effectiveness while meeting all requirements\n2. Proven track record with similar-scale government projects\n3. More detailed migration plan with better risk mitigation\n4. Faster delivery timeline\n5. Comprehensive training program\n\nContract will be signed within 10 business days. All unsuccessful bidders will receive detailed feedback upon request."
}
```

**Expected:**
- Tender status → "awarded"
- Winning bid status → "accepted"
- Other bids status → "rejected"
- Notifications sent to all parties
- Cache invalidated

---

### Phase 12: Rate Limiting Test

#### 12.1 Test Rate Limiting on Root Endpoint
**Endpoint:** `GET /`

**Action:** Click "Execute" button 65+ times rapidly

**Expected:**
- First ~60 requests: 200 OK
- After 60th request: 429 Too Many Requests

**Response (429):**
```json
{
  "error": "Rate limit exceeded: 60 per 1 minute"
}
```

#### 12.2 Test Health Endpoint (Higher Limit)
**Endpoint:** `GET /health`

**Action:** Click "Execute" 205+ times

**Expected:**
- First ~200 requests: Success
- After 200th: 429 errors

---

## Summary Checklist

After completing all tests, you should have:

### ✅ Data Created:
- [ ] 4 Users (1 admin, 1 authority, 2 bidders)
- [ ] 3 Companies (Gov, ACME, Tech Solutions)
- [ ] 2 Tenders (IT Project awarded, Office Supplies published)
- [ ] 2 Bids (1 accepted, 1 rejected)
- [ ] 4+ Documents (tender docs + bid docs)
- [ ] 2 Q&A Threads (both answered)
- [ ] 15+ Notifications

### ✅ Features Tested:
- [ ] User registration and authentication
- [ ] Role-based access control
- [ ] Company management
- [ ] Tender CRUD operations
- [ ] Document upload/download
- [ ] Bidding process
- [ ] Q&A system
- [ ] Notification system
- [ ] Award process
- [ ] Pagination (all list endpoints)
- [ ] Caching (GET endpoints faster on 2nd call)
- [ ] Rate limiting (429 errors after threshold)

---

## Troubleshooting

### Issue: 401 Unauthorized
**Solution:** Click Authorize (🔒) and paste current user's token

### Issue: 403 Forbidden
**Solution:** Check user role - only authorities can publish/award, only bidders can bid

### Issue: 422 Validation Error
**Solution:** Check required fields match the JSON examples

### Issue: Rate limit blocking too early
**Solution:** Wait 60 seconds for limit to reset

### Issue: Cannot see other company's bids
**Solution:** This is correct - bidders only see their own bids until tender is awarded

---

**You're all set!** Follow this guide step-by-step and you'll test every major feature. 🚀

Good luck with your testing!
