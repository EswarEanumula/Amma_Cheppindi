import argparse
import array
import datetime
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import wave
from zoneinfo import ZoneInfo

STATE = Path.home() / ".amma-cheppindi"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
STORIES = [
    ("చిన్న అడుగు", ["ఒక రోజు అమ్మ ఒక చిన్న మొక్క నాటింది.", "రోజూ కొద్దిగా నీళ్లు పోసింది. కొన్ని రోజులకు కొత్త చిగురు వచ్చింది.", "అమ్మ చెప్పింది. పెద్ద మార్పు కూడా చిన్న అడుగుతో మొదలవుతుంది."]),
    ("ఒక మంచి మాట", ["పక్కింటి అమ్మాయి దిగులుగా కూర్చుంది.", "అమ్మ ఆమె పక్కన కూర్చుని, నువ్వు చెప్పాలనుకుంటే నేను వింటాను అంది.", "అమ్మ చెప్పింది. కొన్నిసార్లు మనం ఇచ్చే గొప్ప బహుమతి మన సమయమే."]),
    ("తప్పు నుంచి పాఠం", ["మొదటిసారి వేసిన బొమ్మ నాకు నచ్చలేదు.", "అమ్మ నవ్వి, ఈ గీతను చూడు. దీని నుంచి ఇంకో బొమ్మ మొదలుపెట్టు అంది.", "అమ్మ చెప్పింది. ప్రతి తప్పు మనకు కొత్త దారి చూపించగలదు."]),
]

def run(*args, directory=None):
    subprocess.run(args, cwd=directory, check=True, timeout=240)

def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ], text=True, timeout=30))

def make_score(path, seconds):
    rate = 22050
    notes = (60, 64, 67, 72, 69, 67, 64, 62)
    samples = array.array("h")
    for frame in range(math.ceil(seconds * rate)):
        time = frame / rate
        index = int(time / 0.7)
        age = time % 0.7
        frequency = 440 * 2 ** ((notes[index % len(notes)] - 69) / 12)
        phase = 2 * math.pi * frequency * age
        envelope = min(age / 0.05, 1, (0.7 - age) / 0.18)
        fade = min(time / 0.45, 1, (seconds - time) / 0.8)
        sample = (math.sin(phase) + 0.22 * math.sin(2 * phase)) * envelope * fade
        samples.append(int(3600 * sample))
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(samples.tobytes())

def render(destination, title, scenes):
    with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
        work = Path(scratch)
        for index, caption in enumerate(scenes):
            audio = work / f"voice-{index}.mp3"
            run("edge-tts", "--voice", "te-IN-ShrutiNeural", "--text", caption,
                "--write-media", str(audio))
            length = math.ceil((duration(audio) + 0.65) * 30) / 30
            # libass shapes Telugu and wraps it within the vertical safe area.
            header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Noto Sans Telugu,52,&H00E4F4FF,&H00FFFFFF,&H00402D1F,&H00402D1F,-1,0,0,0,100,100,0,0,1,2,0,8,65,65,170,1
Style: Captions,Noto Sans Telugu,42,&H00FFFFFF,&H00FFFFFF,&H003B2C1D,&H003B2C1D,0,0,0,0,100,100,0,0,1,3,0,2,84,84,220,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            drawing = (
                r"{\an7\pos(0,0)\p1\bord0\1c&H7D9AAC&}m 0 825 l 210 615 390 795 560 650 720 835 720 1280 0 1280"
                r"{\1c&H526E80&}m 0 930 l 285 740 500 920 720 745 720 1280 0 1280"
                r"{\1c&HCDE7FF&}m 490 450 b 490 340 650 340 650 450 b 650 560 490 560 490 450"
            )
            lines = [(0, "Title", drawing), (1, "Title", title), (1, "Captions", caption)]
            (work / "scene.ass").write_text(header + "".join(
                f"Dialogue: {layer},0:00:00.00,0:01:00.00,{style},,0,0,0,,{line}\n"
                for layer, style, line in lines
            ), encoding="utf-8")
            color = ("0x604536", "0x385253", "0x55506B")[index % 3]
            run("ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                f"color=c={color}:s=720x1280:r=30", "-i", str(audio),
                "-vf", "ass=scene.ass", "-af", "apad", "-t", str(length),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "1",
                f"scene-{index}.mp4", directory=work)
        playlist = work / "scenes.txt"
        playlist.write_text("".join(f"file 'scene-{i}.mp4'\n" for i in range(len(scenes))))
        run("ffmpeg", "-loglevel", "error", "-f", "concat", "-safe", "1",
            "-i", "scenes.txt", "-c", "copy", "joined.mp4", directory=work)
        length = duration(work / "joined.mp4")
        if not 5 <= length <= 60:
            raise RuntimeError(f"Unexpected duration: {length:.1f}s")
        make_score(work / "score.wav", length)
        run("ffmpeg", "-loglevel", "error", "-i", "joined.mp4", "-i", "score.wav",
            "-filter_complex",
            "[0:a]volume=0.9[voice];[1:a]volume=0.24[score];[voice][score]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0",
            "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", "final.mp4",
            directory=work)
        os.replace(work / "final.mp4", destination)

def authorize():
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(STATE / "client.json"), SCOPES)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    token = STATE / "token.json"
    with open(os.open(token, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as file:
        file.write(credentials.to_json())

def upload(video, title, mode, receipt):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if "id" in previous:
            print(f"Already uploaded: https://youtu.be/{previous['id']}")
            return
        raise RuntimeError("A previous upload may have finished. Check YouTube Studio before clearing the pending receipt.")
    credentials = Credentials.from_authorized_user_file(str(STATE / "token.json"), SCOPES)
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"{title} | అమ్మ చెప్పింది",
                "description": "అమ్మ చెప్పింది | చిన్న కథ, మంచి మాట. #Shorts",
                "categoryId": "22",
                "defaultLanguage": "te"
            },
            "status": {"privacyStatus": mode, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True),
    )
    with receipt.open("x") as file:
        json.dump({"pending": True}, file)
    response = None
    while response is None:
        _, response = request.next_chunk(num_retries=3)
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps({"id": response["id"], "privacy": response["status"]["privacyStatus"]}))
    os.replace(temporary, receipt)
    if response["status"]["privacyStatus"] != mode:
        raise RuntimeError(f"YouTube returned {response['status']['privacyStatus']} for https://youtu.be/{response['id']}")
    print(f"Uploaded: https://youtu.be/{response['id']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["render", "private", "public", "authorize"])
    mode = parser.parse_args().mode
    STATE.mkdir(mode=0o700, exist_ok=True)
    if mode == "authorize":
        authorize()
    else:
        day = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date()
        # Persist the selected episode for this day across retries and code updates.
        episodes = STATE / "episodes"
        episodes.mkdir(exist_ok=True)
        episode = episodes / f"{day}.json"
        if not episode.exists():
            episode.write_text(json.dumps(STORIES[day.toordinal() % len(STORIES)], ensure_ascii=False))
        title, scenes = json.loads(episode.read_text())
        video = episodes / f"{day}.mp4"
        if not video.exists():
            render(video, title, scenes)
        print(video)
        if mode != "render":
            upload(video, title, mode, episodes / f"{day}.youtube.json")
