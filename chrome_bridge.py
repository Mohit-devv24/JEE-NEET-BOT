import subprocess
import json

def run_js_in_drive_tab(js_code):
    applescript = f'''
    tell application "Google Chrome"
        repeat with w in windows
            set idx to 1
            repeat with t in tabs of w
                try
                    if URL of t contains "1V3GtPtz0YFBndpbs6j7Hq1c8g2aes99Z" then
                        return execute t javascript "{js_code}"
                    end if
                end try
                set idx to idx + 1
            end repeat
        end repeat
        return "NOT_FOUND"
    end tell
    '''
    res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
    return res.stdout.strip()

print("Title:", run_js_in_drive_tab("document.title"))
