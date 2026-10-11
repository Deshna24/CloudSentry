# AWS deployment

CloudSentry runs on AWS in **ap-south-1 (Mumbai)**. This is the deployment submitted for the Cloud Computing mini project.

## Architecture
```
 Browser
    |
    v
 S3 static website (React build)            http://<bucket>.s3-website.ap-south-1.amazonaws.com
    |  API calls (VITE_API_URL)
    v
 Application Load Balancer  (HTTP:80)      security group: cs-alb-sg   <- internet
    |  target group cs-api-tg, port 8000, health check /health/instance
    +--------------------+
    v                    v
 EC2 cs-api-01        EC2 cs-api-02         security group: cs-app-sg   <- only from the ALB
 (AZ ap-south-1a)     (AZ ap-south-1b)      Docker, FastAPI, INSTANCE_ID API-01 / API-02
    \                    /
     v                  v
   RDS PostgreSQL (private, encrypted)      security group: cs-db-sg    <- only from cs-app-sg

 Logs -> CloudWatch Logs (cloudsentry-api)
 Alarm -> CloudWatch (UnHealthyHostCount >= 1) -> SNS topic -> email
```

## Resources
| Layer | Resource | Notes |
|-------|----------|-------|
| Frontend | S3 bucket with static website hosting | public read through a bucket policy; SSE-S3 encryption |
| Load balancing | Application Load Balancer `cs-alb` | internet-facing, two Availability Zones |
| Targets | Target group `cs-api-tg` | HTTP:8000, health check `/health/instance`, interval 10 s, healthy/unhealthy threshold 2 |
| Compute | 2 x EC2 (Amazon Linux, Docker) | one per Availability Zone, no key pair, no SSH |
| Database | RDS PostgreSQL | not publicly accessible, encrypted at rest, SSL required |
| Identity | IAM role `cs-ec2-role` | `AmazonSSMManagedInstanceCore` and `CloudWatchAgentServerPolicy`; no access keys on the servers |
| Monitoring | CloudWatch Logs, CloudWatch alarm, SNS | alarm on `UnHealthyHostCount >= 1` (1 minute, Maximum) |

## Security design
- **Layered security groups (least privilege):** internet -> ALB only; app servers accept port 8000 only from the ALB group; the database accepts port 5432 only from the app group.
- **Private, encrypted database:** no public IP, encryption at rest, SSL connection (`sslmode=require`).
- **No SSH, no stored credentials:** servers are managed through AWS Systems Manager Session Manager; the IAM role supplies permissions.
- **Secrets outside the code:** `DATABASE_URL`, `JWT_SECRET` and seed passwords live in a root-only env file (`chmod 600`) on each server, not in the repository.
- **Application security:** JWT authentication, role-based access control, bcrypt password hashing, and CORS restricted to the S3 website origin.
- **Detection and response:** the rule-based engine scores requests 0-100 and allows, monitors, throttles or blocks them; every decision is written to the audit log.

## Deployment steps (summary)
1. Create the three security groups (`cs-alb-sg`, `cs-app-sg`, `cs-db-sg`) with the rules above.
2. Create the RDS PostgreSQL instance in the default VPC, public access off, attach `cs-db-sg`, set the initial database name `cloudsentry`.
3. Create the IAM role `cs-ec2-role` for EC2.
4. Launch two EC2 instances in different Availability Zones with `cs-app-sg`, the IAM role, no key pair, and the user data below (change `INSTANCE_ID` on the second).
5. Create the target group (HTTP:8000, health check `/health/instance`) and register both instances.
6. Create the Application Load Balancer (HTTP:80, `cs-alb-sg`, both Availability Zones) forwarding to the target group.
7. Build the frontend with `VITE_API_URL=http://<ALB-DNS>` and upload `dist/` to an S3 bucket with static website hosting and a public-read bucket policy.
8. Set `CORS_ORIGINS` on both servers to the S3 website URL and recreate the containers.
9. Create the CloudWatch alarm on `UnHealthyHostCount` with an SNS email notification.

### EC2 user data (values are placeholders)
```bash
#!/bin/bash
dnf install -y docker git
systemctl enable --now docker

cat > /opt/cs.env <<'ENV'
DATABASE_URL=postgresql://<db-user>:<db-password>@<rds-endpoint>:5432/cloudsentry?sslmode=require
JWT_SECRET=<long-random-string>
ENVIRONMENT=production
INSTANCE_ID=API-01
EXPECTED_INSTANCES=API-01,API-02
CORS_ORIGINS=<s3-website-url>
TRUST_PROXY_HEADERS=true
SEED_ADMIN_PASSWORD=<choose>
SEED_ANALYST_PASSWORD=<choose>
ENV
chmod 600 /opt/cs.env

git clone https://github.com/<owner>/CloudSentry.git /opt/cloudsentry
cd /opt/cloudsentry/backend
docker build -t cloudsentry-api .
docker run -d --name api --restart always -p 8000:8000 --env-file /opt/cs.env \
  --log-driver=awslogs --log-opt awslogs-region=ap-south-1 \
  --log-opt awslogs-group=cloudsentry-api --log-opt awslogs-create-group=true \
  cloudsentry-api
```
Never commit real values for the placeholders above.

## Health endpoints
| Endpoint | Purpose |
|----------|---------|
| `/health` | liveness, returns the instance ID |
| `/health/database` | database connectivity and latency |
| `/health/instance` | used by the ALB target group; returns 503 while the instance is in simulated failure, so the ALB drains it |
| `/health/detailed` | used by the dashboard |

## What was verified on the live deployment
- Both instances healthy behind the ALB; refreshing alternates `Served by API-01` and `API-02`.
- **Failover:** "Simulate instance failure" turns one target Unhealthy in the target group while the site keeps serving from the other instance; recovery returns both to Healthy.
- **Attack simulation:** brute-force traffic is detected, scored critical and blocked; incidents appear in Threats, Traffic and Audit logs.
- **Monitoring:** the CloudWatch alarm went to *In alarm* during the failure and sent an email through SNS.

## Cost and shutdown
The ALB, EC2 instances and RDS bill while they run. After evaluation: delete the load balancer and target group, terminate the EC2 instances, delete the RDS instance (skip or keep a final snapshot as needed), empty and delete the S3 bucket, and delete the alarm, SNS topic and log group.
