# AutoCorrect

A high-end, system-wide Python autocorrect daemon with a hardware-accelerated Cyberpunk interface. It fixes misspellings and context errors while you type across all applications.

## 🎨 GUI Features

- **Cyberpunk Aesthetic**: Hardware-accelerated Matrix rain background with Japanese Katakana and glassmorphic panels.
- **System Tray Integration**: Minimizes to the taskbar tray for silent background operation.
- **Statistics Dashboard**: Real-time tracking of words scanned, corrections applied, and latency across Day, Week, Month, and Lifetime periods.
- **Custom Dictionary Manager**: Easily add, remove, and search for words in your personal vocabulary.
- **Unknown Word Logger**: Tracks unrecognized tokens for future dictionary expansion.
- **Master Toggle**: Pause/Resume autocorrect immediately from the interface without quitting.
- **Sliding Indicator Navigation**: Modern, animated UI transitions using `OutExpo` easing curves.

## ⚙️ Core Logic Features

- **Context-Aware Bigrams**: Analyzes the previous word to properly fix confusable words (e.g., `their` vs `they're`).
- **Retroactive Correction**: Automatically reaches back to fix the previous word if context changes (e.g., "their" -> "they're going").
- **Smart Auto-Capitalization**: Capitalizes after `.`, `!`, or `?`.
- **Double Backspace Undo**: Double-tap `Backspace` to immediately revert any correction.

## 🚀 Installation

Install Python, then install the required dependencies:

```bash
pip install pynput PySide6
```

## 🖥️ Usage

Run the GUI to start the daemon and interface:

```bash
python gui.py
```

### Controls & Navigation
- **Statistics Tab**: View your typing efficiency and lifetime data.
- **Dictionary Tab**: Manage your custom words.
- **Diagnostics Panel**: Toggle the master autocorrect engine or the bigram context engine.
- **System Tray**: Right-click the pink icon in your taskbar to restore the window or quit the daemon entirely.

## 📂 Project Structure

```text
AutoCorrect/
├── AutoCorrect.py      # Core processing logic
├── gui.py              # Aesthetic interface
├── stats.json          # Persistent lifetime statistics
├── custom_dict.txt     # Your personal word list
├── unknown.txt         # Log of unrecognized words
├── TRUSTED_WORDS.txt   # Base vocabulary
└── Bigram.txt          # Context data source
```

## 🔧 Customization

To change the **System Tray Icon**, open `gui.py` and modify the `TRAY_ICON_PATH` constant at the top of the file (Line 31). If no file is provided, it defaults to a pink square.

---
*Built with PySide6 for high-performance desktop aesthetics.*
