# Harness 云端 + OpenCloudOS 云服务器：Delegate 安装与 rag_lite 镜像部署指南

本文说明如何在 **Harness SaaS（云端 Harness）** 中，于 **OpenCloudOS** 云主机上安装 **Docker Delegate**，将 **rag_lite** 项目构建为 **Docker 镜像**并持续部署到同一台或指定服务器。按章节顺序执行即可完成端到端流程。

> **官方参考**  
> - [安装 Harness Delegate](https://developer.harness.io/docs/platform/get-started/tutorials/install-delegate)  
> - [Docker Delegate 环境变量](https://developer.harness.io/docs/platform/delegates/delegate-reference/docker-delegate-environment-variables)  
> - [通过 SSH 部署到 VM](https://developer.harness.io/docs/continuous-delivery/deploy-srv-diff-platforms/traditional/ssh-ng)  
> - [物理数据中心（PDC）连接器](https://developer.harness.io/docs/platform/connectors/cloud-providers/pdc-connector)

---

## 一、架构与前提

### 1.1 推荐架构

```
Harness SaaS（控制台）  ──HTTPS 出站──▶  云服务器 OpenCloudOS
                                              ├─ Docker（运行 Delegate 容器）
                                              ├─ Docker（运行 rag_lite 应用容器）
                                              └─ 可选：MySQL、Milvus（docker compose）
```

- **Delegate**：只主动连 Harness，不在公网暴露控制面；用于执行 **构建镜像**、**SSH 部署**、拉取私有仓库等任务。  
- **rag_lite**：Flask 应用，默认监听 `5000`；依赖 **MySQL** 与 **向量库**（默认配置为 **Milvus**，见 `app/config.py`）。

### 1.2 你需要准备的内容

| 项目 | 说明 |
|------|------|
| Harness 账号 | SaaS，可登录 `https://app.harness.io`（或你所在区域的 Harness 地址） |
| 云服务器 | OpenCloudOS，建议 **4 vCPU / 8GB 内存** 及以上（Milvus + 模型推理较吃资源） |
| 镜像仓库 | 如 Docker Hub、阿里云 ACR、Harbor 等（用于推送 `rag-lite` 镜像） |
| 域名或公网 IP | 若需浏览器访问 Web，需安全组放行端口并做好 HTTPS（可选 Nginx） |

### 1.3 rag_lite 运行依赖（务必规划）

应用通过环境变量连接外部服务，部署前请确认：

- **MySQL**：库表需已初始化（按项目迁移/SQL 说明执行）。  
- **Milvus**：仓库内 `docker-compose.yml` 可在服务器上启动单机 Milvus（etcd、minio、standalone）。  
- **嵌入/重排序模型**：首次运行可能下载模型；生产环境建议将模型目录挂载进容器（见下文「镜像与模型」）。  
- **API Key**：如 `DEEPSEEK_API_KEY` 等，通过 Harness Secret 或运行时 `-e` 注入，**不要**写入镜像。

---

## 二、OpenCloudOS 服务器基础环境

以下命令在 **云服务器 SSH** 中执行（需 root 或 sudo）。

### 2.1 安装 Docker 与 Docker Compose 插件

OpenCloudOS 与 RHEL/CentOS 系类似，若尚未安装 Docker：

```bash
# 示例：使用官方 Docker CE 仓库（若你厂商提供一键安装脚本，以其为准）
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
```

确认版本：

```bash
docker version
docker compose version
```

### 2.2 防火墙与安全组

- **云厂商安全组**：至少放行 **22（SSH）**；若外网访问 Web，放行 **5000**（或 **80/443** 若前面有反向代理）。  
- **系统防火墙**（如 firewalld）：按需放行同上端口。

### 2.3（可选）在本机启动 Milvus

在项目目录（含 `docker-compose.yml`）执行：

```bash
cd /path/to/rag_lite
export DOCKER_VOLUME_DIRECTORY=/data/milvus-data   # 建议指定数据盘路径
docker compose up -d
```

Milvus 对外端口默认为 **19530**（见 `docker-compose.yml`）。应用容器内需设置 `MILVUS_HOST` 为可解析的主机名：同机可用 **宿主机网关 IP**（常见为 `172.17.0.1`）或 **host 网络模式**（需自行评估安全与端口冲突）。

### 2.4（可选）安装 MySQL

可使用云厂商 RDS，或在服务器上用 Docker/包管理安装 MySQL 8.x，并创建数据库与用户，与 `DB_*` 环境变量一致。

---

## 三、Harness 控制台准备

### 3.1 创建 Organization / Project

1. 登录 Harness **Next Gen**。  
2. 创建或使用已有 **Organization**。  
3. 创建 **Project**（例如 `rag-lite-prod`），后续连接器、流水线、密钥均建议放在该项目内。

### 3.2 获取 Account ID

浏览器地址栏 URL 中含账户 ID，例如：

`https://app.harness.io/ng/#/account/<你的AccountId>/...`

其中 `<你的AccountId>` 即为 **ACCOUNT_ID**。

### 3.3 创建 Delegate Token

1. 进入 **Account Settings** → **Account Resources** → **Delegates**。  
2. 打开 **Tokens** 页签 → **New Token**，命名后 **复制保存**（仅显示一次或需妥善保管）。

### 3.4 记录 Manager 地址

SaaS 一般为：

- `MANAGER_HOST_AND_PORT=https://app.harness.io`

若你使用其他区域/专属域名，以 Harness 界面安装 Delegate 向导中显示的为准。

---

## 四、在云服务器上安装 Docker Delegate

### 4.1 推荐方式：从界面复制安装命令

1. Harness：**Account Settings** → **Account Resources** → **Delegates** → **New Delegate**。  
2. 选择 **Docker**。  
3. 填写 Delegate 名称（如 `opencloudos-docker-del`），选择刚创建的 **Token**。  
4. 复制界面生成的 **`docker run` 或 `docker compose` 片段**，在服务器上执行。

界面生成的命令已包含镜像名、`ACCOUNT_ID`、`DELEGATE_TOKEN`、`MANAGER_HOST_AND_PORT` 等，**优先使用界面命令**，避免手写错误。

### 4.2 环境变量说明（便于排查）

若需对照或脚本化安装，Docker Delegate 常见变量包括（名称以官方文档为准）：

| 变量 | 含义 |
|------|------|
| `ACCOUNT_ID` | Harness 账户 ID |
| `DELEGATE_TOKEN` | Delegate 注册令牌 |
| `DELEGATE_NAME` | 在 Harness 中显示的 Delegate 名称 |
| `MANAGER_HOST_AND_PORT` | 如 `https://app.harness.io` |
| `NEXT_GEN` | Next Gen 一般为 `true` |

完整列表见：[Docker delegate environment variables](https://developer.harness.io/docs/platform/delegates/delegate-reference/docker-delegate-environment-variables)。

### 4.3 可选：Delegate 标签（与流水线选择器）

在界面或命令中为 Delegate 设置 **Tags**（如 `opencloudos`、`build`），后续在 Connector / Pipeline 中可用 **Delegate Selector** 指定由哪台 Delegate 执行任务。

### 4.4 验证 Delegate 已连接

1. 回到 **Delegates** 列表，状态应为 **Connected / Healthy**。  
2. 若长时间未上线：检查服务器出站 **443** 是否被防火墙拦截；查看容器日志：

```bash
sudo docker ps
sudo docker logs -f <delegate_container_name>
```

### 4.5 CI 构建说明

若流水线需要在 Delegate 所在机上执行 **`docker build`**，请确认：

- Delegate 容器能访问 **Docker 守护进程**（常见做法：挂载 `docker.sock`，具体以 Harness 当前 Docker Delegate 安装模板为准）。  
- 或改用 **Kubernetes Delegate** / **Remote Docker** 等 Harness 支持的构建基础设施。

若界面安装命令已包含 `/var/run/docker.sock` 挂载，通常即可在本机构建镜像。

---

## 五、镜像仓库与 Harness 连接器

### 5.1 在镜像仓库创建仓库

例如：`your-registry/rag-lite`（Docker Hub 为 `用户名/rag-lite`）。

### 5.2 在 Harness 创建 Docker Registry 连接器

1. **Project Settings** → **Connectors** → **New Connector** → **Docker Registry**。  
2. 填写仓库地址、用户名、密码（密码放入 **Secret**）。  
3. **Connection** 测试时选择可访问外网且已安装 Docker 的 **Delegate**（即上一节安装的 Delegate）。

记录连接器名称，供 CI/CD 引用。

---

## 六、构建 rag_lite 镜像（本地验证）

项目根目录已提供 `Dockerfile` 与 `.dockerignore`。

### 6.1 本地构建与运行（自测）

```bash
cd /path/to/rag_lite
docker build -t your-registry/rag-lite:latest .

# 示例运行（请按实际修改环境变量；MySQL/Milvus 需可达）
docker run -d --name rag-lite -p 5000:5000 \
  -e DB_HOST=... \
  -e DB_PASSWORD=... \
  -e MILVUS_HOST=... \
  -e DEEPSEEK_API_KEY=... \
  your-registry/rag-lite:latest
```

### 6.2 模型与持久化目录（生产建议）

- 大模型文件不建议打进镜像；在服务器准备目录，例如 `/data/rag/models`，下载 README 中说明的嵌入与重排序模型后，在 `docker run` 中 **`-v /data/rag/models:/app/embeddingModels`** 等（路径需与代码中加载逻辑一致）。  
- 上传文件、Chroma 持久化目录等同样建议 **volume 挂载**，避免容器删除后数据丢失。

### 6.3 环境变量清单（参考）

与 `app/config.py` 对应，常用包括：`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`、`VECTOR_DB_TYPE`、`MILVUS_HOST`、`MILVUS_PORT`、`STORAGE_TYPE`、`MINIO_*`、`DEEPSEEK_API_KEY`、`APP_PORT` 等。生产务必将 `APP_DEBUG` 设为 `false`。

---

## 七、Harness CI：构建并推送镜像

目标：在 Delegate 上执行 `docker build` 和 `docker push`。

### 7.1 准备代码仓库

将 `rag_lite` 推送到 **GitHub / GitLab / Bitbucket** 等，并在 Harness 创建对应 **Code Connector**（或使用 Harness 支持的 Git 源）。

### 7.2 创建 Pipeline（CI）

1. 在 Project 中 **Create Pipeline**。  
2. 添加 **Build** 阶段，基础设施选择 **Use Docker delegate**（或绑定带 Docker 的 Delegate）。  
3. 添加步骤（名称因模块略有差异，以界面为准）：  
   - **Git Clone**（或由 Pipeline 自动检出）。  
   - **Build and Push Docker Registry**：  
     - Dockerfile 路径：`Dockerfile`  
     - Context：仓库根目录  
     - Image：`your-registry/rag-lite`  
     - Tag：如 `<+pipeline.sequenceId>` 或 `latest` + 分支名  
   - 绑定上一节的 **Docker Registry 连接器**。

4. 保存并 **Run Pipeline**，确认镜像已出现在仓库中。

> 若构建失败：多半是依赖体积大（PyTorch/sentence-transformers）导致超时或内存不足——可适当调大 Delegate 主机资源，或在 Dockerfile 中采用分阶段构建、镜像缓存等优化（进阶话题）。

---

## 八、Harness CD：部署到 OpenCloudOS（SSH 方式）

目标：在目标机上 `docker pull` 并 `docker run`（或 `compose`）新版本。

### 8.1 服务器 SSH 与密钥

1. 在目标云服务器创建专用部署用户（如 `deploy`），配置 **公钥登录**。  
2. 将 **私钥** 存入 Harness **Secret**（SSHKey 类型）。  
3. 确保 **Delegate 能通过 SSH 访问该主机**（同机时为 `127.0.0.1` 或内网 IP；跨机为内网 IP 并做好安全组）。

### 8.2 创建 SSH / PDC 连接器

1. 参考 [PDC 连接器](https://developer.harness.io/docs/platform/connectors/cloud-providers/pdc-connector) 与 [SSH 部署](https://developer.harness.io/docs/continuous-delivery/deploy-srv-diff-platforms/traditional/ssh-ng)。  
2. 配置主机、SSH 凭证、**Delegate**（与执行部署的 Delegate 一致或路由可达）。

### 8.3 Service 与 Artifact

1. 创建 **Service**，制品类型选择 **Docker**，指向同一镜像仓库与镜像名。  
2. 运行时配置可用 **Harness 文件存储** 或模板化脚本注入 `.env`（勿把密钥明文写入仓库）。

### 8.4 部署步骤（思路）

在 **SSH** 部署类型的工作流中，执行脚本示例（需按你的镜像名、网络、卷挂载改写）：

```bash
set -e
docker login -u "$REG_USER" -p "$REG_PASS" your-registry
docker pull your-registry/rag-lite:<+artifact.tag>
docker stop rag-lite || true
docker rm rag-lite || true
docker run -d --name rag-lite --restart unless-stopped -p 5000:5000 \
  --env-file /opt/rag-lite/.env \
  -v /data/rag/file_storage:/app/file_storage \
  your-registry/rag-lite:<+artifact.tag>
```

其中 `REG_USER` / `REG_PASS`、`.env` 路径等通过 Harness **Runtime input** 或 **Secrets** 注入。

### 8.5 同机 Delegate + 同机应用

若 Delegate 与应用在同一台机器，SSH 指向 `127.0.0.1` 即可；注意 **权限**：`deploy` 用户需在 `docker` 组内或使用 root（按安全规范择优）。

---

## 九、联调检查清单

1. **Delegate**：Harness 控制台显示健康。  
2. **CI**：镜像成功推送到仓库。  
3. **CD**：SSH 执行成功，容器 `docker ps` 可见。  
4. **应用**：`curl http://服务器IP:5000` 或浏览器访问首页。  
5. **依赖**：MySQL 连接、Milvus `19530`、对象存储（若用 MinIO）均从容器内可达。  
6. **日志**：`docker logs rag-lite` 与项目 `logs` 目录。

---

## 十、常见问题

| 现象 | 可能原因 |
|------|----------|
| Delegate 无法连接 | 出站 HTTPS 被墙；`MANAGER_HOST_AND_PORT` 错误；时钟偏差过大 |
| CI docker build 失败 | 内存/磁盘不足；未挂载 `docker.sock`；Dockerfile 路径错误 |
| 应用启动但无法连库 | `DB_HOST` 填了 `localhost`（在容器内指向容器自身）；应填宿主机 IP 或服务名 |
| Milvus 连不上 | `MILVUS_HOST` 在 bridge 网络下不能写 `127.0.0.1`；改用网关 IP 或 host 网络 |

---

## 十一、文档与仓库文件对应关系

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 构建应用镜像 |
| `.dockerignore` | 减小构建上下文、排除敏感与无用文件 |
| `docker-compose.yml` | 单机 Milvus 依赖（etcd/minio/standalone） |
| `docs/Harness云端部署指南.md` | 本文 |

按 **第二节 → 第四节 → 第五节 → 第七节 → 第八节** 顺序执行，即可在 Harness 云端完成 **Delegate 安装 → 镜像构建推送 → SSH 部署** 的闭环。若你后续改用 **Kubernetes**，可将 Delegate 与 CD 改为 Helm/K8s 部署方式，Harness 官方文档中有对应教程。
