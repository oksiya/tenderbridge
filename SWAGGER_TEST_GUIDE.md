# Swagger UI Manual Testing Guide

**Date:** October 15, 2025  
**Purpose:** Step-by-step manual testing of all endpoints with fresh data

---

## Prerequisites

### 1. Access Swagger UI
```
http://localhost:8000/docs
```

### 2. Truncate All Tables (Fresh Start)
```bash
# Connect to database
podman exec -it tenderbridge_db_1 psql -U postgres -d tenderbridge

# Truncate tables (in order to respect foreign keys)
TRUNCATE TABLE qa_responses CASCADE;
TRUNCATE TABLE qa_questions CASCADE;
TRUNCATE TABLE documents CASCADE;
TRUNCATE TABLE bids CASCADE;
TRUNCATE TABLE tenders CASCADE;
TRUNCATE TABLE notifications CASCADE;
TRUNCATE TABLE companies CASCADE;
TRUNCATE TABLE users CASCADE;

# Exit
\q
```

---

## Testing Workflow

### Phase 1: User Management & Authentication

#### 1.1 Register Company Admin
**Endpoint:** `POST /auth/register`

```json
{
  "email": "admin@acmecorp.com",
  "password": "SecurePass123!",
  "full_name": "John Smith",
  "role": "company_admin",
  "company_name": "ACME Corporation",
  "company_address": "123 Business St, Tech City, TC 12345",
  "company_tax_id": "TAX-123456789",
  "company_registration": "REG-ACME-2025"
}
```

**Expected:** User created with company, returns access token  
**Note:** Save the `access_token` for authentication

#### 1.2 Register Contracting Authority
**Endpoint:** `POST /auth/register`

```json
{
  "email": "procurement@govagency.gov",
  "password": "GovSecure456!",
  "full_name": "Sarah Johnson",
  "role": "contracting_authority",
  "company_name": "Government Procurement Agency",
  "company_address": "456 Government Plaza, Capital City, CC 54321",
  "company_tax_id": "GOV-987654321",
  "company_registration": "GOV-AGENCY-2025"
}
```

**Expected:** Authority user created, returns access token  
**Note:** Save this `access_token` separately

#### 1.3 Register Bidder
**Endpoint:** `POST /auth/register`

```json
{
  "email": "sales@techsolutions.com",
  "password": "BidPass789!",
  "full_name": "Michael Chen",
  "role": "bidder",
  "company_name": "Tech Solutions Inc",
  "company_address": "789 Innovation Drive, Startup Valley, SV 67890",
  "company_tax_id": "TAX-555666777",
  "company_registration": "REG-TECH-2025"
}
```

**Expected:** Bidder created, returns access token  
**Note:** Save this `access_token` for bidding

#### 1.4 Login Test
**Endpoint:** `POST /auth/login`

```json
{
  "username": "admin@acmecorp.com",
  "password": "SecurePass123!"
}
```

**Expected:** Returns new access token

---

### Phase 2: Authentication Setup in Swagger

**Click the "Authorize" button (🔒) at the top of Swagger UI**

1. In the "HTTPBearer (http, Bearer)" field, paste your access token
2. Format: Just paste the token (no "Bearer" prefix needed)
3. Click "Authorize"
4. Click "Close"

**You're now authenticated! The lock icon (🔒) should show as locked.**

---

### Phase 3: Company Management

#### 3.1 Get My Company
**Endpoint:** `GET /companies/me`

**Expected:** Returns your company details
```json
{
  "id": 1,
  "name": "ACME Corporation",
  "address": "123 Business St, Tech City, TC 12345",
  "tax_id": "TAX-123456789",
  "registration_number": "REG-ACME-2025",
  "created_at": "2025-10-15T...",
  "updated_at": "2025-10-15T..."
}
```

#### 3.2 Update Company
**Endpoint:** `PUT /companies/me`

```json
{
  "name": "ACME Corporation Ltd",
  "address": "123 Business St, Suite 500, Tech City, TC 12345",
  "tax_id": "TAX-123456789",
  "registration_number": "REG-ACME-2025"
}
```

**Expected:** Returns updated company info

---

### Phase 4: Tender Management

#### 4.1 Create Tender (as Contracting Authority)
**Switch to Authority Token:** Authorize with the procurement@govagency.gov token

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

**Expected:** Tender created with status "draft"  
**Note:** Save the tender `id` (let's assume it's `1`)

#### 4.2 Create Another Tender
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
**Note:** Save this tender `id` (let's assume it's `2`)

#### 4.3 Get All Tenders (Test Pagination)
**Endpoint:** `GET /tenders/`

**Parameters:**
- `skip`: 0
- `limit`: 10

**Expected:** Paginated list with 2 tenders
```json
{
  "items": [...],
  "total": 2,
  "skip": 0,
  "limit": 10,
  "has_more": false
}
```

#### 4.4 Get Tender Details (Test Caching)
**Endpoint:** `GET /tenders/{tender_id}`

**Path Parameter:** `tender_id` = 1

**Expected:** Full tender details
**Test Caching:** Call this endpoint twice and check response time (second should be faster)

#### 4.5 Update Tender
**Endpoint:** `PUT /tenders/{tender_id}`

**Path Parameter:** `tender_id` = 1

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

#### 4.6 Publish Tender
**Endpoint:** `PUT /tenders/{tender_id}/status`

**Path Parameter:** `tender_id` = 1

**Request Body:**
```json
{
  "status": "published"
}
```

**Expected:** Tender status changes to "published"

#### 4.7 Publish Second Tender
**Endpoint:** `PUT /tenders/{tender_id}/status`

**Path Parameter:** `tender_id` = 2

**Request Body:**
```json
{
  "status": "published"
}
```

**Expected:** Second tender published

---

### Phase 5: Document Management

#### 5.1 Upload Tender Document
**Endpoint:** `POST /tenders/{tender_id}/upload`

**Path Parameter:** `tender_id` = 1

**Form Data:**
- `file`: Choose a PDF file (create a dummy PDF or use any PDF)
- `document_type`: "requirements"
- `description`: "Detailed technical specifications and requirements"

**Expected:** Document uploaded and linked to tender

#### 5.2 Upload Another Document
**Endpoint:** `POST /tenders/{tender_id}/upload`

**Path Parameter:** `tender_id` = 1

**Form Data:**
- `file`: Choose another file
- `document_type`: "other"
- `description`: "Reference architecture diagrams"

**Expected:** Second document uploaded

#### 5.3 List Tender Documents
**Endpoint:** `GET /documents/tender/{tender_id}`

**Path Parameter:** `tender_id` = 1

**Expected:** List of 2 documents

#### 5.4 Download Document
**Endpoint:** `GET /documents/{document_id}/download`

**Path Parameter:** Use `document_id` from previous response

**Expected:** File download starts

---

### Phase 6: Bidding Process

#### 6.1 Switch to Bidder Account
**Authorize with:** sales@techsolutions.com token (from Phase 1.3)

#### 6.2 Create Bid
**Endpoint:** `POST /bids/`

```json
{
  "tender_id": 1,
  "amount": 485000.00,
  "proposal": "# Tech Solutions Inc - IT Infrastructure Proposal\n\n## Executive Summary\nTech Solutions Inc is pleased to submit our comprehensive proposal for the IT Infrastructure Upgrade Project. With over 8 years of experience in enterprise IT and successful completion of 15+ government projects, we are uniquely positioned to deliver this critical initiative.\n\n## Our Approach\n1. **Assessment Phase** (Weeks 1-2)\n   - Complete infrastructure audit\n   - Risk assessment\n   - Migration planning\n\n2. **Implementation Phase** (Weeks 3-12)\n   - Phased rollout to ensure zero downtime\n   - Parallel running of old and new systems\n   - Daily progress reports\n\n3. **Testing & Optimization** (Weeks 13-14)\n   - Comprehensive testing\n   - Performance optimization\n   - Security audits\n\n4. **Training & Handover** (Weeks 15-16)\n   - Staff training programs\n   - Documentation delivery\n   - 90-day support period\n\n## Cost Breakdown\n- Hardware & Software: $285,000\n- Implementation Services: $120,000\n- Training & Documentation: $35,000\n- Support & Maintenance (Year 1): $45,000\n\n**Total: $485,000**\n\n## Certifications\n- ISO 27001:2013\n- ISO 9001:2015\n- CMMI Level 3\n- Government Approved Vendor (GAV-2024)\n\n## Timeline\nProject completion: 16 weeks from contract signing\n\n## Guarantee\nZero-downtime migration guarantee backed by performance bonds.",
  "delivery_time": 112
}
```

**Expected:** Bid created with status "submitted"  
**Note:** Save the bid `id`

#### 6.3 Upload Bid Document
**Endpoint:** `POST /bids/{bid_id}/upload`

**Path Parameter:** Use the bid `id` from above

**Form Data:**
- `file`: Upload a file (PDF or other)
- `document_type`: "proposal"
- `description`: "Detailed technical proposal and implementation plan"

**Expected:** Document attached to bid

#### 6.4 Upload Financial Document
**Endpoint:** `POST /bids/{bid_id}/upload`

**Form Data:**
- `file`: Upload another file
- `document_type`: "financial"
- `description`: "Cost breakdown and payment schedule"

**Expected:** Second document attached

#### 6.5 Create Second Bid (Different Bidder)
**Switch to:** admin@acmecorp.com token (ACME Corporation)

**Endpoint:** `POST /bids/`

```json
{
  "tender_id": 1,
  "amount": 520000.00,
  "proposal": "# ACME Corporation - Infrastructure Modernization Proposal\n\n## Company Overview\nACME Corporation brings 12 years of experience in large-scale IT infrastructure projects, specializing in government and enterprise clients.\n\n## Our Solution\nWe propose a cutting-edge, cloud-first architecture leveraging:\n- Multi-cloud strategy (AWS + Azure)\n- Kubernetes orchestration\n- Zero-trust security model\n- AI-powered monitoring\n\n## Project Phases\n### Phase 1: Discovery & Planning (3 weeks)\n- Infrastructure assessment\n- Cloud readiness evaluation\n- Security audit\n- Custom migration strategy\n\n### Phase 2: Cloud Foundation (4 weeks)\n- Cloud infrastructure setup\n- Network configuration\n- Security implementation\n- Compliance verification\n\n### Phase 3: Migration (8 weeks)\n- Phased application migration\n- Data migration with validation\n- Legacy system decommissioning\n- Performance optimization\n\n### Phase 4: Stabilization (3 weeks)\n- Monitoring implementation\n- Performance tuning\n- Staff training\n- Documentation\n\n## Investment Breakdown\n- Cloud Infrastructure (3-year): $180,000\n- Migration Services: $215,000\n- Security & Compliance: $75,000\n- Training & Support: $50,000\n\n**Total: $520,000**\n\n## Value Proposition\n- 40% reduction in operational costs\n- 99.99% uptime SLA\n- Quantum-ready encryption\n- 24/7/365 support\n- Industry-leading certifications\n\n## Guarantees\n- Performance bond covering full project value\n- Zero-downtime migration guarantee\n- 12-month warranty period\n- Fixed price commitment",
  "delivery_time": 126
}
```

**Expected:** Second bid created

#### 6.6 List All Bids for Tender (Test Caching)
**Switch to:** Contracting Authority token (procurement@govagency.gov)

**Endpoint:** `GET /bids/tender/{tender_id}`

**Path Parameter:** `tender_id` = 1

**Expected:** List of 2 bids (call twice to test caching)

#### 6.7 Get Bid Details
**Endpoint:** `GET /bids/{bid_id}`

**Path Parameter:** Use first bid `id`

**Expected:** Full bid details with documents

#### 6.8 Update Bid Status
**Endpoint:** `PUT /bids/{bid_id}/status`

**Path Parameter:** Use first bid `id`

**Request Body:**
```json
{
  "status": "under_review"
}
```

**Expected:** Bid status updated to "under_review"

---

### Phase 7: Q&A System

#### 7.1 Switch to Bidder Account
**Authorize with:** sales@techsolutions.com token

#### 7.2 Ask Question
**Endpoint:** `POST /qa/questions`

```json
{
  "tender_id": 1,
  "question": "Regarding the quantum-ready encryption requirement: Could you please clarify the specific quantum algorithms and key sizes expected? Are you looking for post-quantum cryptography standards like CRYSTALS-Kyber or CRYSTALS-Dilithium?"
}
```

**Expected:** Question created with status "pending"  
**Note:** Save the question `id`

#### 7.3 Ask Another Question
**Endpoint:** `POST /qa/questions`

```json
{
  "tender_id": 1,
  "question": "The requirements mention zero-downtime migration. Can you please confirm if this applies to all systems including the mainframe applications, or only the newer distributed systems? Also, what is the acceptable service degradation threshold during migration?"
}
```

**Expected:** Second question created

#### 7.4 Switch to Authority Account
**Authorize with:** procurement@govagency.gov token

#### 7.5 List Questions for Tender
**Endpoint:** `GET /qa/tenders/{tender_id}/questions`

**Path Parameter:** `tender_id` = 1

**Expected:** List of 2 questions

#### 7.6 Answer Question
**Endpoint:** `POST /qa/questions/{question_id}/answer`

**Path Parameter:** Use first question `id`

**Request Body:**
```json
{
  "answer": "Thank you for your question. For the quantum-ready encryption requirement:\n\n1. We expect implementation of NIST-approved post-quantum cryptography algorithms, specifically:\n   - CRYSTALS-Kyber for key encapsulation (minimum security level 3)\n   - CRYSTALS-Dilithium for digital signatures (minimum security level 3)\n\n2. The solution should be compatible with FIPS 203 and FIPS 204 standards\n\n3. Hybrid approach is acceptable during transition period (combining classical and post-quantum algorithms)\n\n4. All encryption must support minimum 256-bit security level equivalent\n\nPlease ensure your proposal addresses crypto-agility to support future algorithm updates."
}
```

**Expected:** Question answered, status changes to "answered"

#### 7.7 Answer Second Question
**Endpoint:** `POST /qa/questions/{question_id}/answer`

**Path Parameter:** Use second question `id`

**Request Body:**
```json
{
  "answer": "Excellent question regarding zero-downtime requirements:\n\n1. **Scope**: Zero-downtime applies to:\n   - All web-based applications\n   - Email systems\n   - File servers\n   - Public-facing services\n\n2. **Mainframe applications**: We understand these may require brief maintenance windows. Acceptable approach:\n   - Maximum 2-hour downtime window per application\n   - Must be scheduled outside business hours (10 PM - 6 AM)\n   - Requires 2-week advance notice\n   - Maximum 3 such windows for entire project\n\n3. **Service degradation threshold**:\n   - Response time: No more than 20% increase during migration\n   - Availability: 99.9% minimum during migration period\n   - Transaction processing: No degradation in throughput\n\n4. **Monitoring**: Real-time monitoring required with automated rollback if thresholds exceeded\n\nPlease reflect this in your migration plan and provide specific mitigation strategies."
}
```

**Expected:** Second question answered

#### 7.8 Get Question with Answer
**Switch to:** Any authenticated user

**Endpoint:** `GET /qa/questions/{question_id}`

**Path Parameter:** Use first question `id`

**Expected:** Full question with answer displayed

---

### Phase 8: Notifications

#### 8.1 Get My Notifications
**Endpoint:** `GET /notifications/`

**Parameters:**
- `skip`: 0
- `limit`: 20
- `is_read`: (leave empty for all)

**Expected:** Paginated list of notifications
- Tender status changes
- Bid submissions
- Q&A activities
- System notifications

#### 8.2 Get Unread Count
**Endpoint:** `GET /notifications/unread-count`

**Expected:**
```json
{
  "count": 5
}
```

#### 8.3 Mark Notification as Read
**Endpoint:** `PUT /notifications/{notification_id}/read`

**Path Parameter:** Use any notification `id` from the list

**Expected:** Notification marked as read

#### 8.4 Mark All as Read
**Endpoint:** `PUT /notifications/mark-all-read`

**Expected:** All notifications marked as read

#### 8.5 Verify Unread Count Again
**Endpoint:** `GET /notifications/unread-count`

**Expected:**
```json
{
  "count": 0
}
```

---

### Phase 9: Award Process

#### 9.1 Switch to Authority Account
**Authorize with:** procurement@govagency.gov token

#### 9.2 Award Tender
**Endpoint:** `POST /tenders/{tender_id}/award`

**Path Parameter:** `tender_id` = 1

**Request Body:**
```json
{
  "winning_bid_id": 1,
  "award_notes": "After careful evaluation of both proposals, the committee has decided to award this contract to Tech Solutions Inc based on the following criteria:\n\n**Technical Evaluation (40 points)**\n- Tech Solutions: 38/40\n- ACME Corporation: 35/40\n\n**Financial Evaluation (30 points)**\n- Tech Solutions: 28/30 (more competitive pricing)\n- ACME Corporation: 24/30\n\n**Experience & References (30 points)**\n- Tech Solutions: 27/30\n- ACME Corporation: 28/30\n\n**Total Scores:**\n- Tech Solutions Inc: 93/100 ✓ WINNER\n- ACME Corporation: 87/100\n\n**Key Decision Factors:**\n1. Superior cost-effectiveness while meeting all requirements\n2. Proven track record with similar-scale government projects\n3. More detailed migration plan with better risk mitigation\n4. Faster delivery timeline\n5. Comprehensive training program\n\nContract will be signed within 10 business days. All unsuccessful bidders will receive detailed feedback upon request."
}
```

**Expected:**
- Tender status changes to "awarded"
- Winning bid status changes to "accepted"
- Other bids status changes to "rejected"
- Notifications sent to all bidders
- Cache invalidated

#### 9.3 Verify Tender Status
**Endpoint:** `GET /tenders/{tender_id}`

**Path Parameter:** `tender_id` = 1

**Expected:** Status = "awarded", winning_bid_id populated

#### 9.4 Check Winning Bid
**Endpoint:** `GET /bids/{bid_id}`

**Path Parameter:** Use winning bid `id` (1)

**Expected:** Status = "accepted"

---

### Phase 10: Rate Limiting Test

#### 10.1 Test Rate Limiting
**Endpoint:** `GET /` (root endpoint)

**Action:** Click "Execute" rapidly 65+ times

**Expected:**
- First ~60 requests: Success (200 OK)
- Requests 61+: Rate limited (429 Too Many Requests)

**Response (429):**
```json
{
  "error": "Rate limit exceeded: 60 per 1 minute"
}
```

#### 10.2 Test Health Endpoint (Higher Limit)
**Endpoint:** `GET /health`

**Action:** Click "Execute" rapidly 205+ times

**Expected:**
- First ~200 requests: Success
- Requests 201+: Rate limited

---

### Phase 11: User Profile & Admin

#### 11.1 Get Current User
**Endpoint:** `GET /users/me`

**Expected:** Your user profile with company info

#### 11.2 Update User Profile
**Endpoint:** `PUT /users/me`

```json
{
  "full_name": "John Smith Jr.",
  "email": "admin@acmecorp.com"
}
```

**Expected:** Profile updated

#### 11.3 List All Users (Admin Only)
**Endpoint:** `GET /users/`

**Expected:** List of all registered users

---

## Verification Checklist

After completing all tests, verify:

### ✅ Core Functionality
- [ ] User registration works for all roles
- [ ] Authentication and JWT tokens work
- [ ] Company management CRUD operations
- [ ] Tender creation and publishing
- [ ] Bid submission and evaluation
- [ ] Document upload and download
- [ ] Q&A system workflow
- [ ] Notification system
- [ ] Award process

### ✅ Production Features
- [ ] **Pagination**: All list endpoints return paginated responses
- [ ] **Caching**: Second calls to GET endpoints are faster
- [ ] **Rate Limiting**: Excessive requests return 429 errors

### ✅ Security
- [ ] Unauthorized requests return 401
- [ ] Role-based access control works
- [ ] Bidders cannot see other bids before award
- [ ] Only authorities can publish tenders
- [ ] Only authorities can award tenders

### ✅ Notifications
- [ ] Notifications created for all major events
- [ ] Unread count updates correctly
- [ ] Mark as read functionality works

---

## Database State After Testing

You should have:
- **3 Users**: Authority, Bidder 1 (Tech Solutions), Bidder 2 (ACME)
- **3 Companies**: Gov Agency, Tech Solutions, ACME Corp
- **2 Tenders**: IT Infrastructure (awarded), Office Supplies (published)
- **2 Bids**: Both for IT Infrastructure tender
- **4+ Documents**: Tender docs + Bid docs
- **2 Q&A Questions**: Both answered
- **15+ Notifications**: Various events

---

## Troubleshooting

### Issue: "Unauthorized" errors
**Solution:** Click "Authorize" button and paste your JWT token

### Issue: "422 Validation Error"
**Solution:** Check required fields in the JSON payload

### Issue: Rate limiting kicking in too early
**Solution:** Wait 60 seconds and try again

### Issue: File upload fails
**Solution:** Ensure file size is under limit (check config)

### Issue: Cache not working (responses equally fast)
**Solution:** This is fine - with small dataset, database is already fast

---

## Next Steps

After manual testing:
1. **Document Issues**: Note any bugs or unexpected behavior
2. **Review Phase 4**: Confirm all production features work
3. **Plan Phase 5**: Discuss advanced features if needed
4. **Production Deployment**: Follow PHASE4_COMPLETE.md checklist

---

**Happy Testing! 🚀**

Let me know if you find any issues during testing!
