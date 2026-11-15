import subprocess
import time

def run_js(js):
    escaped = js.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ")
    sc = f"""
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                try
                    if URL of t contains "1V3GtPtz0YFBndpbs6j7Hq1c8g2aes99Z" then
                        return execute t javascript "try {{ {escaped} }} catch(e) {{ e.toString() }}"
                    end if
                end try
            end repeat
        end repeat
    end tell
    """
    p = subprocess.run(["osascript", "-e", sc], capture_output=True, text=True)
    return p.stdout.strip()

js = """
(function() {
    let text = [];
    document.querySelectorAll("div").forEach(d => {
        let t = d.innerText || "";
        if (t.includes("Zipping") || t.includes("Preparing download") || t.includes("Download ready")) {
            if (t.length > 3 && t.length < 80) text.push(t.trim());
        }
    });
    return Array.from(new Set(text)).join(" | ");
})()
"""

for i in range(12):
    res = run_js(js)
    print(f"[{i+1}/12] Status: {res}")
    time.sleep(5)
