# MonoZone Pi Controller

REST API server for controlling Monoprice 6-Zone Audio via iTach Flex. Runs on Raspberry Pi and includes scheduling support for automated zone control.

## Architecture

```
iOS App  ──HTTP──►  Raspberry Pi  ──TCP──►  iTach Flex  ──RS232──►  Monoprice 6-Zone
                    (this service)          (IP-RS232)              Amplifier
```

## Installation

SSH into your Raspberry Pi and run:

```bash
# Clone the repository
cd ~
git clone https://github.com/twolfekc/monozone-pi.git
cd monozone-pi

# Run the install script
chmod +x install.sh
./install.sh

# Configure the iTach IP address
nano config.py
# Change ITACH_HOST to your iTach's IP address
# Save with Ctrl+X, Y, Enter

# Start the service
sudo systemctl start monozone
sudo systemctl status monozone
```

## Verify Installation

```bash
curl http://localhost:8080/api/health
# Should return: {"status": "ok"}

curl http://localhost:8080/api/status
# Shows connection status to iTach
```

## Updating

After pushing changes from your development machine:

```bash
cd ~/monozone-pi
git pull
sudo systemctl restart monozone
```

## Useful Commands

```bash
sudo systemctl status monozone      # Check if running
sudo systemctl restart monozone     # Restart service
sudo systemctl stop monozone        # Stop service
sudo journalctl -u monozone -f      # View live logs
sudo journalctl -u monozone -n 50   # View last 50 log lines
```

## API Endpoints

### Zone Control
- `GET /api/zones` - Get all zone states
- `GET /api/zones/{id}` - Get single zone state
- `POST /api/zones/{id}/power` - Set power `{"on": true/false}`
- `POST /api/zones/{id}/volume` - Set volume `{"volume": 0-38}`
- `POST /api/zones/{id}/source` - Set source `{"source": 1-6}`
- `POST /api/zones/{id}/mute` - Set mute `{"muted": true/false}`
- `POST /api/zones/all/power` - Set all zones power

### Schedules
- `GET /api/schedules` - List all schedules
- `POST /api/schedules` - Create schedule
- `PUT /api/schedules/{id}` - Update schedule
- `DELETE /api/schedules/{id}` - Delete schedule
- `POST /api/schedules/{id}/toggle` - Enable/disable
- `POST /api/schedules/{id}/run` - Execute immediately

### System
- `GET /api/status` - Pi status and connection state
- `GET /api/health` - Health check

## Configuration

Edit `config.py` to set:
- `ITACH_HOST` - IP address of your iTach Flex
- `ITACH_PORT` - TCP port (default: 4999)
- `API_PORT` - API server port (default: 8080)
