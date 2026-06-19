# ob-dashboard
Web dashboard to see Orangeboxes' availability

## How to run

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example configuration file and fill in your values:

```bash
cp config.example.env .env
```

| Variable | Description | Default |
|---|---|---|
| `ORANGEBOXES_FILE` | Path to JSON file listing orangeboxes with hostname and IP | `orangeboxes.json` |
| `OB_HOST` | IP address or hostname of one orangebox (used for ping/power check) | _(none)_ |
| `OB_HOSTS` | Optional fallback comma-separated list of orangeboxes when inventory file is unavailable | _(none)_ |
| `MAAS_URL` | Base URL of the MAAS server, e.g. `http://10.0.0.1:5240/MAAS` | _(none)_ |
| `MAAS_API_KEY` | MAAS API key in `consumer_key:token_key:token_secret` format – obtain from MAAS UI → your account → API keys | _(none)_ |
| `PORT` | Port the web server listens on | `5000` |
| `FLASK_DEBUG` | Set to `1` to enable Flask debug mode (do not use in production) | `0` |

Example `orangeboxes.json`:

```json
[
	{"hostname": "ob-01", "ip": "172.27.24.1"},
	{"hostname": "ob-02", "ip": "192.168.250.24"}
]
```

Export the variables before starting the app:

```bash
export ORANGEBOXES_FILE=orangeboxes.json
export OB_HOST=172.27.24.1
export OB_HOSTS=172.27.24.1,172.27.24.2
export MAAS_URL=http://172.27.24.1:5240/MAAS
export MAAS_API_KEY=consumer_key:token_key:token_secret
```

### 4. Start the application

```bash
python app.py
```

Open your browser at <http://localhost:5000>.

### 5. Run the tests

```bash
python -m pytest tests/
```
