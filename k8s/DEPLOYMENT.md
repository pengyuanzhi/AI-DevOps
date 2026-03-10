# Kubernetes Deployment Guide

This guide covers deploying the AI-CICD platform to Kubernetes.

## Prerequisites

1. **Kubernetes Cluster**: Version 1.24+
2. **kubectl**: Configured to access your cluster
3. **Helm 3+** (Optional, for additional services)
4. **Container Registry**: Access to push/pull Docker images
5. **Ingress Controller**: NGINX Ingress Controller recommended

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    API       │  │   Worker     │  │   Celery     │      │
│  │  (Deployment)│  │ (Deployment) │  │    Beat      │      │
│  │   HPA: 3-10  │  │  HPA: 4-20   │  │  (1 replica) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                                 │
│         └─────────────────┼─────────────────┐               │
│                           │                 │               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │    Redis     │  │   RabbitMQ   │      │
│  │(StatefulSet) │  │ (Deployment) │  │(StatefulSet) │      │
│  │   1 replica  │  │   1 replica  │  │   1 replica  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           │                                 │
│  ┌────────────────────────┴────────────────────────┐       │
│  │              Ingress (NGINX)                    │       │
│  │         ai-cicd.example.com                     │       │
│  └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Steps

### 1. Build and Push Container Image

```bash
# Build the Docker image
docker build -t your-registry.com/ai-cicd:v1.0.0 .

# Push to registry
docker push your-registry.com/ai-cicd:v1.0.0
```

### 2. Create Namespace

```bash
kubectl apply -f k8s/base/namespace.yaml
```

### 3. Create Secrets

Create a file `production.env` with your secrets:

```bash
# LLM API Keys
ANTHROPIC_API_KEY=your_actual_anthropic_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
OPENAI_API_KEY=your_actual_openai_api_key
ZHIPU_API_KEY=your_actual_zhipu_api_key
ZHIPU_MODEL=glm-4-plus
DEFAULT_LLM_PROVIDER=zhipu

# GitLab Configuration
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_actual_gitlab_token
GITLAB_WEBHOOK_SECRET=generate_random_webhook_secret

# Database Credentials
POSTGRES_DB=ai_cicd
POSTGRES_USER=ai_cicd
POSTGRES_PASSWORD=generate_secure_password_here

# Redis Password
REDIS_PASSWORD=generate_secure_password_here

# RabbitMQ Credentials
RABBITMQ_USER=ai_cicd
RABBITMQ_PASSWORD=generate_secure_password_here
RABBITMQ_VHOST=/
```

Then create the secret:

```bash
kubectl create secret generic ai-cicd-secrets \
  --from-env-file=production.env \
  -n ai-cicd
```

### 4. Deploy Base Infrastructure

```bash
# Deploy ConfigMap, PostgreSQL, Redis, RabbitMQ
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/postgres.yaml
kubectl apply -f k8s/base/redis.yaml
kubectl apply -f k8s/base/rabbitmq.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n ai-cicd --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n ai-cicd --timeout=180s
kubectl wait --for=condition=ready pod -l app=rabbitmq -n ai-cicd --timeout=180s
```

### 5. Run Database Migrations

```bash
# Port-forward to PostgreSQL
kubectl port-forward -n ai-cicd svc/postgres 5432:5432

# In another terminal, run migrations
python scripts/migrate_db.py upgrade
```

### 6. Deploy Application

```bash
# Update image in k8s/base/deployment.yaml or use Kustomize
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/service.yaml
kubectl apply -f k8s/base/hpa.yaml
```

### 7. Deploy Ingress

Update `k8s/base/service.yaml` with your actual domain, then:

```bash
kubectl apply -f k8s/base/service.yaml
```

### 8. Verify Deployment

```bash
# Check pod status
kubectl get pods -n ai-cicd

# Check services
kubectl get svc -n ai-cicd

# Check HPA status
kubectl get hpa -n ai-cicd

# View logs
kubectl logs -f deployment/ai-cicd-api -n ai-cicd
kubectl logs -f deployment/ai-cicd-worker -n ai-cicd
```

## Kustomize Deployment (Recommended)

For environment-specific configurations, use Kustomize:

### Development

```bash
kubectl apply -k k8s/base
```

### Production

```bash
# Create production secrets first
kubectl create secret generic ai-cicd-secrets \
  --from-env-file=production.env \
  -n ai-cicd

# Apply production manifests
kubectl apply -k k8s/production
```

## Monitoring and Maintenance

### View Logs

```bash
# API logs
kubectl logs -f deployment/ai-cicd-api -n ai-cicd

# Worker logs
kubectl logs -f deployment/ai-cicd-worker -n ai-cicd

# Specific pod logs
kubectl logs -f <pod-name> -n ai-cicd

# All pods logs
kubectl logs -f -l app=ai-cicd -n ai-cicd --all-containers=true
```

### Port Forwarding (Local Development)

```bash
# Forward API to localhost
kubectl port-forward -n ai-cicd svc/ai-cicd-api 8000:80

# Forward PostgreSQL
kubectl port-forward -n ai-cicd svc/postgres 5432:5432

# Forward Redis
kubectl port-forward -n ai-cicd svc/redis 6379:6379

# Forward RabbitMQ Management UI
kubectl port-forward -n ai-cicd svc/rabbitmq-management 15672:15672
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment/ai-cicd-api --replicas=5 -n ai-cicd
kubectl scale deployment/ai-cicd-worker --replicas=10 -n ai-cicd

# HPA will auto-scale based on traffic
kubectl get hpa -n ai-cicd -w
```

### Updating

```bash
# Rolling update
kubectl set image deployment/ai-cicd-api \
  api=your-registry.com/ai-cicd:v1.1.0 \
  -n ai-cicd

kubectl set image deployment/ai-cicd-worker \
  worker=your-registry.com/ai-cicd:v1.1.0 \
  -n ai-cicd

# Watch rollout status
kubectl rollout status deployment/ai-cicd-api -n ai-cicd
kubectl rollout status deployment/ai-cicd-worker -n ai-cicd

# Rollback if needed
kubectl rollout undo deployment/ai-cicd-api -n ai-cicd
```

### Database Backups

```bash
# Backup PostgreSQL
kubectl exec -n ai-cicd postgres-0 -- pg_dump \
  -U ai_cicd ai_cicd > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
cat backup_20240308.sql | kubectl exec -i -n ai-cicd postgres-0 -- psql \
  -U ai_cicd ai_cicd
```

## Resource Requirements

### Minimum (Development)

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| API | 250m | 512Mi | - |
| Worker | 500m | 1Gi | - |
| PostgreSQL | 500m | 1Gi | 10Gi |
| Redis | 100m | 256Mi | 2Gi |
| RabbitMQ | 250m | 512Mi | 5Gi |
| **Total** | **1.6 cores** | **3.3Gi** | **17Gi** |

### Production (Recommended)

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| API (3-10 pods) | 1.5-5 cores | 3-10Gi | - |
| Worker (4-20 pods) | 4-20 cores | 8-40Gi | - |
| PostgreSQL | 1-2 cores | 2-4Gi | 50-100Gi |
| Redis | 250-500m | 512Mi-1Gi | 10-20Gi |
| RabbitMQ | 500m-1 core | 1-2Gi | 20-50Gi |
| **Total** | **7-28 cores** | **15-57Gi** | **80-170Gi** |

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod for events
kubectl describe pod <pod-name> -n ai-cicd

# Check pod logs
kubectl logs <pod-name> -n ai-cicd

# Check previous container logs (if crashed)
kubectl logs <pod-name> -n ai-cicd --previous
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
kubectl run -it --rm psql-test --image=postgres:15 --restart=Never \
  -- psql postgresql://ai_cicd:password@postgres:5432/ai_cicd -n ai-cicd
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n ai-cicd
kubectl top nodes

# Check HPA metrics
kubectl describe hpa -n ai-cicd
```

## Security Considerations

1. **Secrets Management**:
   - Use external secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
   - Rotate secrets regularly
   - Never commit secrets to git

2. **Network Policies**:
   - Restrict pod-to-pod communication
   - Only allow necessary traffic

3. **RBAC**:
   - Create service accounts with minimal permissions
   - Use RoleBindings and ClusterRoleBindings

4. **TLS**:
   - Enable TLS for all external communication
   - Use cert-manager for automatic certificate management

## Next Steps

1. Set up monitoring (Prometheus, Grafana)
2. Configure centralized logging (ELK, Loki)
3. Set up alerting rules
4. Configure backup and disaster recovery
5. Implement GitOps (ArgoCD, Flux) for deployment automation
