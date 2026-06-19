# ob-dashboard
Web dashboard to see Orangeboxes' availability

## How to run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example configuration file and fill in your values:

```bash
cp config.example.env .env
```

| Variable | Description | Default |
|---|---|---|
| `OB_HOST` | IP address or hostname of the orangebox (used for ping/power check) | _(none)_ |
| `MAAS_URL` | Base URL of the MAAS server, e.g. `http://10.0.0.1:5240/MAAS` | _(none)_ |
| `MAAS_API_KEY` | MAAS API key in `consumer_key:token_key:token_secret` format – obtain from MAAS UI → your account → API keys | _(none)_ |
| `PORT` | Port the web server listens on | `5000` |
| `FLASK_DEBUG` | Set to `1` to enable Flask debug mode (do not use in production) | `0` |

Export the variables before starting the app:

```bash
export OB_HOST=10.0.0.1
export MAAS_URL=http://10.0.0.1:5240/MAAS
export MAAS_API_KEY=consumer_key:token_key:token_secret
```

### 3. Start the application

```bash
python app.py
```

Open your browser at <http://localhost:5000>.

### 4. Run the tests

```bash
python -m pytest tests/
```
