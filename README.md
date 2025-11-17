# IPv4 Subnet Calculator

A web-based IPv4 subnet calculator built with Flask that provides comprehensive network information and subnet analysis.

## Features

- **Flexible Input Formats**: Accepts CIDR notation (e.g., `192.168.1.1/24`), IP with subnet mask (e.g., `192.168.1.1 255.255.255.0`), or IP with wildcard mask (e.g., `192.168.1.1 0.0.0.255`)
- **Comprehensive Network Information**:
  - Network address and broadcast address
  - Subnet mask (decimal and binary)
  - Wildcard mask
  - Usable host IP range
  - Number of usable hosts
  - IP class (A, B, C, D, E)
  - IP type (Private/Public)
  - in-addr.arpa reverse DNS notation
- **Subnet List View**: Displays all possible subnets within a parent network with pagination
- **Dark/Light Theme**: Toggle between dark and light modes with preference persistence
- **Copy Summary**: One-click copy of all network information in a formatted text format
- **Responsive Design**: Works on desktop and mobile devices

## Requirements

- Python 3.12+
- Flask 2.3.3

## Installation

### Local Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ipcalc
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The application will be available at `http://127.0.0.1:5001`

### Docker Installation

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

2. The application will be available at `http://localhost:5001`

### Docker (Standalone)

1. Build the Docker image:
```bash
docker build -t ipcalc .
```

2. Run the container:
```bash
docker run -p 5001:5001 ipcalc
```

## Usage

1. Enter an IP address in one of the following formats:
   - CIDR notation: `192.168.1.1/24`
   - IP with subnet mask: `192.168.1.1 255.255.255.0`
   - IP with wildcard mask: `192.168.1.1 0.0.0.255`
   - Single IP (defaults to /32): `192.168.1.1`

2. Click "Calculate" to view network information

3. Use the "Copy Summary" button to copy all network details to your clipboard

4. Toggle between dark and light themes using the theme button

5. Navigate through subnet lists using the pagination controls (if applicable)

## Project Structure

```
ipcalc/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── style.css         # Stylesheet
    ├── favicon.ico       # Favicon
    └── favicon-180.png   # Apple touch icon
```

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Network Calculations**: Python `ipaddress` library
- **Containerization**: Docker, Docker Compose
