# Upload and deploy (Google Cloud Run)

This bundle is prepared for a source upload to Cloud Run without GitHub. It has not been deployed.

## Before you start

- A Google Cloud account and project with billing enabled are required.
- Cloud Run has a monthly free usage allowance, not a guarantee of zero charges. Usage beyond the free allowance and related build/storage/network services may incur charges. Review current pricing and consider creating a billing budget alert before deployment.
- This app has no sign-in gate. If deployed with public access, anyone with its URL can use it. Do not enter sensitive farm records into a public demo.
- The app's NASA POWER integration needs no API key. No credentials are included in this bundle. Optional source credentials are not needed for the current app behavior.

## Upload from a browser

1. Create/select a Google Cloud project and enable billing and the Cloud Run/Cloud Build APIs.
2. Open Google Cloud Shell in the browser.
3. Use Cloud Shell's Upload action to upload the ZIP archive named cloud_run_upload.zip.
4. In Cloud Shell, run:

       unzip cloud_run_upload.zip -d agricultural-optimization
       cd agricultural-optimization
       gcloud config set project YOUR_PROJECT_ID
       gcloud run deploy agricultural-optimization --source . --region us-central1 --allow-unauthenticated --port 8080 --memory 1Gi --cpu 1 --max 2

5. Follow the prompts to enable services and confirm public access. Cloud Run prints the app URL after deployment.

Replace YOUR_PROJECT_ID with your project ID. The --max 2 setting caps the maximum number of concurrent instances; it does not guarantee a zero bill.

## Files in the upload bundle

Application modules: app.py, nasa_api.py, recommendations.py, irrigation_plans.py, visualizations.py, crop_rotation.py, and data_sources.py.

Runtime/build files: requirements.txt, Dockerfile, and .dockerignore.

Documentation: README.md and this DEPLOYMENT.md.

## Data and credentials

NASA POWER is requested at runtime from its official API; the app does not ship with a climate dataset or a NASA API key. Other APIs may return missing, unavailable, or unauthenticated statuses. Do not add credentials to this source folder or ZIP. Configure any future required secrets through Cloud Run's secret/environment configuration only after implementing and verifying that connector.

The Docker build installs packages listed in requirements.txt. The container binds Streamlit to Cloud Run's PORT (8080 by default), and runs as a non-root user.
