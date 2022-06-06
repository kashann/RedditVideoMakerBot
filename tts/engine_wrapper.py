from pathlib import Path
from typing import Tuple
import re
from mutagen.mp3 import MP3
from rich.progress import track
from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
from utils.console import print_step, print_substep

class TTSEngine:

    """Calls the given TTS engine to reduce code duplication and allow multiple TTS engines.

    Args:
        tts_module          : The TTS module. Your module should handle the TTS itself and saving to the given path under the run method.
        reddit_object         : The reddit object that contains the posts to read.
        path (Optional)       : The unix style path to save the mp3 files to. This must not have leading or trailing slashes.
        max_length (Optional) : The maximum length of the mp3 files in total.

    Notes:
        tts_module must take the arguments text and filepath.
    """

    def __init__(self, tts_module, reddit_object: dict, path: str = "assets/mp3", max_length: int = 50):
        self.tts_module = tts_module
        self.reddit_object = reddit_object
        self.path = path
        self.max_length = max_length
        self.length = 0

    def run(self) -> Tuple[int, int]:

        Path(self.path).mkdir(parents=True, exist_ok=True)

        # This file needs to be removed in case this post does not use post text, so that it wont appear in the final video
        try:
            Path(f"{self.path}/posttext.mp3").unlink()
        except OSError as e:
            pass

        print_step("Saving Text to MP3 files...")

        self.call_tts("title", self.reddit_object["thread_title"])

        if self.reddit_object["thread_post"] != "":
            self.call_tts("posttext", self.reddit_object["thread_post"])

        for idx, comment in track(enumerate(self.reddit_object["comments"]), "Saving..."):
            # ! Stop creating mp3 files if the length is greater than max length.
            if self.length > self.max_length:
                break
            if not self.tts_module.max_chars:
                self.call_tts(f"{idx}",comment["comment_body"])
            else:
                self.split_post(comment["comment_body"], idx)

        print_substep("Saved Text to MP3 files successfully.", style="bold green")
        return self.length, idx

    def split_post(self, text: str, idx:int) -> str:
        split_files = []
        split_text = [x.group().strip() for x in re.finditer(fr' *((.{{0,{self.tts_module.max_chars}}})(\.|.$))', text)]
        for idy, text_cut in enumerate(split_text):
            print(f"{idx}-{idy}: {text_cut}\n")
            self.call_tts(f"{idx}-{idy}.part", text_cut)
            split_files.append(AudioFileClip(f"{self.path}/{idx}-{idy}.part.mp3"))
        CompositeAudioClip([concatenate_audioclips(split_files)]).write_audiofile(f"{self.path}/{idx}.mp3", fps=44100, verbose=False, logger=None)

        for i in range(0, idy + 1):
            print(f"Cleaning up {self.path}/{idx}-{i}.part.mp3")
            Path(f"{self.path}/{idx}-{i}.part.mp3").unlink()

    def call_tts(self, filename: str, text: str):
        self.tts_module.run(text=text, filepath=f"{self.path}/{filename}.mp3")
        self.length += MP3(f"{self.path}/{filename}.mp3").info.length
