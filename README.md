# Vision Lab Platform

An industrial visual-inspection platform for managing datasets and models, preparing images, running defect-detection inference, and reviewing results. The application consists of a Vue 3 + Vite frontend and a FastAPI + MySQL backend.

## Features

- User registration and login with administrator-managed accounts
- Dataset upload, image annotation, preprocessing, and train/validation/test splitting
- Model management, single-image and dataset inference, and result export
- Industrial case studies, AI training mentor, and AI assistant
- Browser camera access where the browser and deployment environment permit it

## Repository Layout

```text
backend/    FastAPI application and database initialization scripts
frontend/   Vue 3 + Vite application
```

## Requirements

- Ubuntu Server 22.04/24.04 or Windows for local development
- Python 3.10 (the backend dependencies are pinned/tested for this version)
- Node.js 20.19+ or 22.12+ and npm (required by Vite 7)
- MySQL 8.0 (the current model uses MySQL-specific column types)
- Nginx for a public deployment

The included PyTorch packages are CPU builds. Inference runs on CPU unless you deliberately install and configure a compatible GPU build. A small CPU-only server is suitable for a demo or a few concurrent users; it is not a guarantee of 100-user simultaneous model inference. For a class-sized deployment, benchmark expected image sizes and concurrency, and use a GPU or queue inference jobs.

## 1. Clone the Source

```bash
git clone https://github.com/z23728930-ops/vision-lab-platform.git
cd vision-lab-platform
```

## 2. Create a MySQL Database

Create a database and a dedicated account. The backend user also needs permission to create tables during first-time initialization. Replace the example password before running this SQL; do not use the example password on a public server.

```sql
CREATE DATABASE vision_lab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vision_lab_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON vision_lab.* TO 'vision_lab_app'@'localhost';
FLUSH PRIVILEGES;
```

## 3. Configure and Start the Backend

```bash
cd backend
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install the CPU PyTorch wheels from the official PyTorch CPU index, then install the other dependencies:

```bash
python -m pip install torch==2.7.1+cpu torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu
grep -vE '^(torch==|torchvision==)' requirements.txt > /tmp/vision-lab-requirements.txt
python -m pip install -r /tmp/vision-lab-requirements.txt
```

Create `backend/.env` (do not commit it):

```dotenv
DATABASE_URL=mysql+pymysql://vision_lab_app:URL_ENCODED_PASSWORD@127.0.0.1:3306/vision_lab?charset=utf8mb4
SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS_LONG
UPLOADS_DIR=uploads

SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-provider-app-password
SMTP_SENDER_EMAIL=your-email@example.com
SMTP_PORT=465

LLM_ENABLED=false
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

`SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_SENDER_EMAIL` are required by the current settings. Use an email-provider app password, not your mailbox login password. Email notifications are sent only when SMTP credentials are valid and the user has an email address. Encode reserved characters in the MySQL password for the URL (for example, `@` becomes `%40`). Generate a new random `SECRET_KEY` for every installation. Do not reuse secrets from another server.

Initialize tables and create the first administrator interactively:

```bash
python -m scripts.init_db
python -m scripts.create_admin
```

The administrator password is entered without echo and is stored only as a password hash. Public registration creates ordinary student accounts only. Start the backend for a local smoke test:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

API health check: `http://127.0.0.1:8001/`; interactive API docs: `http://127.0.0.1:8001/docs`.

## 4. Build the Frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run build
```

The production files are created in `frontend/dist`. For local development instead, run `npm run dev`; Vite proxies `/api` and `/static_uploads` to `http://127.0.0.1:8001` by default. Override that development target with `VITE_BACKEND_URL` if needed. This Vite proxy is not the production web server.

## 5. Public Deployment with Nginx

Serve the contents of `frontend/dist` from Nginx. Configure the same Nginx virtual host to:

- Use `try_files $uri $uri/ /index.html` for Vue history routes.
- Proxy `/api/` to `http://127.0.0.1:8001/api/`.
- Proxy `/static_uploads/` to `http://127.0.0.1:8001/static_uploads/`.
- Forward WebSocket upgrade headers on `/api/v1/hardware/camera/stream`.
- Set an appropriate upload body limit for model and dataset files.
- Enable HTTPS. Browser camera access requires HTTPS (except localhost).

Run Uvicorn under a process manager such as systemd, bound to `127.0.0.1`; do not expose the backend port directly to the internet. Keep MySQL private to the host/network. Back up both the MySQL database and the `backend/uploads/` directory.

Example Nginx and systemd templates are in `deploy/`. Before using them, create a `visionlab` system account, make the application code readable by it and `backend/uploads` writable by it, then adjust `server_name` and installation paths to match your server. Install the systemd unit as `/etc/systemd/system/vision-lab.service` and the Nginx site as `/etc/nginx/sites-available/vision-lab`; enable both services and validate Nginx configuration before reloading. Configure HTTPS for the site before using camera features.

## 6. Add Models and Datasets

Database initialization creates empty tables; it does not restore the previous server's users, records, models, datasets, or inference history. After logging in as the new administrator:

1. Open **Model Management** and upload a compatible `.pt`, `.pth`, `.tar`, or `.onnx` file. Select the matching type: `yolo`, `faster_rcnn`, or `unet_cbam`. The model weights must match the selected architecture and this application's runner implementation.
2. Open **Dataset Management** and upload a ZIP containing supported image files (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, or `.webp`). The ZIP's image folder structure is preserved. Dataset metadata such as `classes.txt` is retained, but the upload flow does not import existing annotation records from an old database.
3. For a model/data pair that uses application-specific naming conventions, keep the expected names. For the QK workflow, name the dataset `qk` and register its compatible Faster R-CNN model with name `qk` and type `faster_rcnn`.

Large model weights and datasets are distributed separately from this public source repository. Add your own trusted download links below; do not publish private access codes or passwords in this README.

- Model package: _add your file-sharing link_
- QK dataset package: _add your file-sharing link_

## Troubleshooting

- **Database connection error:** check MySQL service status, database/user grants, `.env` location, and URL-encode special characters in `DATABASE_URL`.
- **Missing tables:** activate the backend virtual environment and run `python -m scripts.init_db` from `backend/`.
- **Model file not found after restart:** keep the uploaded model file in `backend/uploads/models`; the database row alone does not contain the weights.
- **Inference fails to load a checkpoint:** verify the model type, checkpoint architecture, class count, and framework version are compatible.
- **Camera is unavailable on a public website:** open the site over HTTPS and grant browser camera permission. The browser can access the student's local camera; the server-side camera endpoint instead accesses a camera attached to the server.
- **Vite reports an unsupported Node version:** install a Node.js 20.19+ or 22.12+ release, then rerun `npm ci`.

## Security and Data

Never commit `.env`, database dumps, uploaded weights, student records, SSH keys, or API/email credentials. Use unique strong secrets and passwords. The public registration endpoint creates only ordinary users. This repository currently does not include a database migration framework; `init_db.py` creates missing tables for a fresh installation but does not migrate existing schemas.

## License

No license has been added to this repository. Contact the project maintainers before reuse or redistribution.
