# Vigil API Reference

## Base URL
```
http://localhost:5000
```

## Authentication
Most endpoints require authentication via headers or query parameters.

---

## Endpoints

### Health & Status

#### Health Check
```
GET /api/health
```

**Response:**
```json
{
  "ok": true,
  "db": "ok"
}
```

---

### Incidents

#### List Incidents
```
GET /api/incidents?camera_id=CAM-001&type=violence&limit=50&offset=0
```

**Query Parameters:**
- `camera_id` (optional): Filter by camera
- `type` (optional): Filter by type (violence, crash)
- `status` (optional): Filter by status (active, resolved, cleared)
- `limit` (optional): Records per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "incidents": [
    {
      "external_id": "inc-abc123",
      "camera_id": "CAM-001",
      "type": "violence",
      "confidence": 0.85,
      "timestamp": "2026-02-08T10:30:00Z",
      "status": "active",
      "acknowledged": false
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### Get Incident Details
```
GET /api/incidents/{external_id}
```

**Response:**
```json
{
  "external_id": "inc-abc123",
  "camera_id": "CAM-001",
  "type": "violence",
  "severity": "high",
  "confidence": 0.85,
  "location": "Main Entrance",
  "timestamp": "2026-02-08T10:30:00Z",
  "description": "Violence detected with multiple people",
  "status": "active",
  "acknowledged": false,
  "ack_by": null,
  "assigned_security": "security@vigil.com",
  "video_url": "/videos/incident-abc123.mp4",
  "actions": [
    {
      "id": 1,
      "action": "created",
      "actor": "AI System",
      "timestamp": "2026-02-08T10:30:00Z"
    }
  ]
}
```

#### Acknowledge Incident
```
POST /api/incidents/{external_id}/ack
Content-Type: application/json

{
  "user_email": "officer@vigil.com"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Incident acknowledged"
}
```

#### Clear Incidents (New Demo Run)
```
POST /api/incidents/clear
```

**Response:**
```json
{
  "status": "success",
  "message": "Incidents cleared for new demo run",
  "new_run_id": "run-xyz789"
}
```

---

### Cameras

#### List Cameras
```
GET /api/cameras
```

**Response:**
```json
{
  "cameras": [
    {
      "id": "CAM-001",
      "name": "Main Entrance",
      "location": "Front Door",
      "is_active": true,
      "event": "normal",
      "last_update": "2026-02-08T10:35:21Z"
    }
  ],
  "total": 12
}
```

#### Get Camera Details
```
GET /api/cameras/{camera_id}
```

**Response:**
```json
{
  "id": "CAM-001",
  "name": "Main Entrance",
  "location": "Front Door",
  "stream_url": null,
  "is_active": true,
  "created_at": "2026-02-08T00:00:00Z",
  "recent_incidents": [
    {
      "external_id": "inc-abc123",
      "type": "violence",
      "timestamp": "2026-02-08T10:30:00Z"
    }
  ]
}
```

---

### Reports

#### Generate Incident Report
```
GET /api/reports/incidents?start_date=2026-02-01&end_date=2026-02-08
```

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `camera_id` (optional): Filter by camera
- `format` (optional): pdf, json, csv (default: json)

**Response (JSON):**
```json
{
  "id": "report-xyz123",
  "name": "Incident Report",
  "type": "incident_summary",
  "generated_at": "2026-02-08T10:45:00Z",
  "period": {
    "start": "2026-02-01",
    "end": "2026-02-08"
  },
  "summary": {
    "total_incidents": 45,
    "by_type": {
      "violence": 20,
      "crash": 25
    },
    "by_camera": {
      "CAM-001": 15,
      "CAM-002": 10
    },
    "avg_confidence": 0.78,
    "status_breakdown": {
      "active": 5,
      "resolved": 40
    }
  }
}
```

---

### Demo Requests

#### Submit Demo Request
```
POST /api/demo-request
Content-Type: application/json

{
  "fullName": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-0123",
  "organization": "Police Department",
  "role": "Lieutenant",
  "cameras": "5-10",
  "message": "Interested in surveillance capabilities"
}
```

**Response:**
```json
{
  "id": "req-abc123",
  "status": "pending",
  "created_at": "2026-02-08T10:50:00Z",
  "message": "Demo request received, we'll contact you soon"
}
```

---

### Videos

#### Stream Video
```
GET /videos/{filename}
```

**Query Parameters:**
- `start` (optional): Start time in seconds
- `duration` (optional): Duration to stream in seconds

**Response:** Video file (stream)

---

### WebSocket Events (Socket.IO)

#### Connect
```javascript
const socket = io('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected');
});
```

#### Listen for Incidents
```javascript
socket.on('incident_update', (incident) => {
  console.log('New incident:', incident);
  // Update dashboard in real-time
});
```

#### Listen for Camera Status
```javascript
socket.on('camera_update', (camera) => {
  console.log('Camera status updated:', camera);
});
```

#### Emit Events
```javascript
// Acknowledge incident
socket.emit('ack_incident', {
  incident_id: 'inc-abc123',
  user: 'officer@vigil.com'
});
```

---

## Error Responses

### Bad Request (400)
```json
{
  "error": "Invalid parameters",
  "details": "camera_id is required"
}
```

### Unauthorized (401)
```json
{
  "error": "Unauthorized",
  "message": "Authentication required"
}
```

### Not Found (404)
```json
{
  "error": "Not found",
  "message": "Incident not found"
}
```

### Server Error (500)
```json
{
  "error": "Internal server error",
  "message": "Database connection failed"
}
```

---

## Rate Limiting

- **Per IP**: 100 requests per minute
- **Per User**: 1000 requests per hour

Headers returned with rate limit info:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1707389400
```

---

## Pagination

Use `limit` and `offset` for pagination:
```
GET /api/incidents?limit=20&offset=40
```

Returns items 40-59.

---

## Filtering & Sorting

Incidents can be filtered and sorted:

```
GET /api/incidents?type=violence&status=active&sort=-timestamp
```

Available sort fields:
- `timestamp`: Incident time
- `confidence`: Detection confidence
- `created_at`: Creation time

Prefix with `-` for descending order.

---

## Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `204 No Content`: Success with no content
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service down

