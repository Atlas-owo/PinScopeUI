The Module Code is in the folder Master, and the Base code is in the folder Slave.

## 🔌 Communication Methods (通信方式)

All commands support **BOTH CAN and UART** communication methods:

- **CAN Bus**: Master → Slave (for system-wide control)
- **UART Serial**: PC → Slave directly (for individual debugging and configuration)

## 🔍 Diagnostics & Monitoring (诊断与监控)

The system includes a robust distributed diagnostic system to monitor the state of all Slave modules via the Master.

### 1. Global Status Query (全局状态查询)
- **Trigger**: Send the character `?` via **Master UART**.
- **Action**: The Master will poll all 50 Slaves sequentially via CAN bus.
- **Report Content**:
  - Motor status and limit switch states.
  - Speed settings (Init & Max).
  - Fan temperature thresholds.
  - UP/DOWN button configurations (Direction, Height, LED colors).
  - Current motor position/height.

### 2. Real-time Temperature Monitoring (实时温度监控)
- **Automatic Reporting**: Slaves automatically report their temperature to the Master if it changes by more than 1°C.
- **Display**: The Master prints these reports to **UART** (and sends them via LAN if connected).
- **Format**: `(Module X) PCB: 35C; Air: 40C; Motor: 30C`

### 3. Boot-up Diagnostic (开机自动诊断)
- **Action**: Upon power-on, the Master waits for 3 seconds for all Slaves to initialize and then automatically performs a global status query.
- **Requirement**: Connect to the Master UART at boot to see the initial system state.

## ⚠️ Safety Features (安全特性)
- **Height Limit**: All motor movements are restricted to a maximum of **200mm**. Any input height exceeding 200 will be capped at 200 automatically.
- **Overheat Protection**: If the motor temperature exceeds 50°C, the motor will enter a protection mode (stops stepping) until it cools down to prevent damage.

## 📋 Command Protocol

- s: 1 - Move the motor to the set position.
  
  `{"i":0,"s":1,"h":[0,0,0,0,0,0,0,0]}`
{"i":0,"s":1,"h":[20,20,20,20,0,0,0,0]}
- s: 2 - Move the motor to the home position.<span style="color:red;"><strong>(Not used)</strong></span>
- s: 3 - Check the init state of the motor. (Not used)
- s: 4 - Set the side (auto). <span style="color:red;"><strong>(Remove)</strong></span>
- s: 5 - Set the speed. ⚡**Supports UART**
  `{"i":0,"s":5,"h":[5,00,2,00,0,0,0,0]}`, 500 is the starting speed, 200 is the ending speed.
  `{"i":0,"s":5,"h":[2,00,1,00,0,0,0,0]}`
  max speed: `{"i":0,"s":5,"h":[1,00,0,50,0,0,0,0]}`
- s: 6 - test mode. (Not used)
- s: 7 - Set the fan's operating temperature. `{"i":0,"s":7,"h":[30,50,0,0,0,0,0,0]}`, 30 is the temperature to start the fan, 50 is the temperature to close the motor. ⚡**Supports UART**
- s: 8 - Set UP/DOWN button configuration. ⚡**Supports UART**
  `{"i":0,"s":8,"h":[1,50,255,0,0,0,50,0,255,0]}`
  Format: `[up_dir, up_height, up_r, up_g, up_b, down_dir, down_height, down_r, down_g, down_b]`
  - `up_dir`: UP button direction (1=increase, 0=decrease)
  - `up_height`: UP button step size in mm
  - `up_r, up_g, up_b`: UP button LED color (RGB 0-255)
  - `down_dir`: DOWN button direction (1=increase, 0=decrease)
  - `down_height`: DOWN button step size in mm
  - `down_r, down_g, down_b`: DOWN button LED color (RGB 0-255)

- s: 9 - Control individual motor LED. ⚡**Supports UART**
  `{"i":0,"s":9,"h":[1,50,255,0,0,0,0,0]}`
  Format: `h[0]=motor_id (1-8), h[1]=R, h[2]=G, h[3]=B, h[4-6]=0, h[7]=reset_flag`

Examples:
- `{"i":0,"s":1,"h":[50,200,100,150,150,100,200,50]}`
- `{"i":0,"s":1,"h":[0,0,0,0,0,0,0,0]}`

