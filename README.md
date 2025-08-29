# Tetris

A classic Tetris game implemented in Python using the Pygame library. The game features smooth piece movement, rotation, line clearing, scoring, and a highscore server integration using a Flask backend and Redis storage.

## Features

- Seven classic Tetris pieces (I, O, T, S, Z, J, L) with rotation and spawning positions.
- Smooth piece falling with adjustable fall speed and fast drop.
- Line clearing with scoring based on the number of lines cleared simultaneously (1 to 4).
- Score and highscore tracking with server integration for storing and fetching highscores using Flask.
- Sidebar displaying next piece preview, current score, highscore, FPS, drop speed, and controls.
- Adjustable FPS for performance tuning.
- Game over screen with options to restart or quit.
- Robust piece and board collision detection for valid moves.
- Responsive keyboard controls for move, rotate, soft drop, and hard drop.

## Requirements

- Python 3.7+
- Pygame
- Requests
- Python-dotenv

All requirements will be installed through requirements.txt

## Installation

1. Clone the repository or download the source code.

    ```bash
    git clone https://github.com/SidoJain/Tetris-V2.git
    ```

2. Install the required Python packages using pip:

    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the project root with the following content:

    ```.env
    TETRIS_SERVER_URL=https://tetris-v2-backend.vercel.app
    ```

    If you do not provide a server URL, the game won't connect to the highscore server and any highscore operation will not be completed.

## Usage

Run the game with:

```bash
cd scripts/
python tetris.py
```
