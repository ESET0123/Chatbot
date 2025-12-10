# voice_to_text.py
import subprocess
import uuid
import os
import io
from pydub import AudioSegment

def convert_audio_to_text(audio_bytes):
    """
    Convert audio bytes to text using Whisper
    """
    temp_input = f"temp_{uuid.uuid4()}.webm"
    temp_output = f"temp_{uuid.uuid4()}.wav"
    
    try:
        # Save the incoming audio
        with open(temp_input, "wb") as f:
            f.write(audio_bytes)
        
        # Convert to WAV format using pydub (handles various formats)
        try:
            audio = AudioSegment.from_file(temp_input)
            audio = audio.set_frame_rate(16000).set_channels(1)  # Whisper prefers 16kHz mono
            audio.export(temp_output, format="wav")
        except Exception as e:
            print(f"Audio conversion error: {e}")
            # If pydub fails, try using the file directly
            temp_output = temp_input
        
        # Try multiple whisper command variations
        whisper_commands = [
            ["whisper", temp_output, "--model", "base", "--language", "en"],
            ["whisper", temp_output, "--model", "tiny", "--language", "en"],
            ["whisper", temp_output],
        ]
        
        result = None
        for cmd in whisper_commands:
            try:
                print(f"Trying command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and result.stdout:
                    break
            except Exception as e:
                print(f"Command failed: {e}")
                continue
        
        if result and result.returncode == 0:
            # Parse whisper output
            output = result.stdout
            print("Whisper output:", output)
            
            # Try to extract transcribed text
            if "->" in output:
                text = output.split("->")[1].strip()
            elif "[" in output and "]" in output:
                # Format: [00:00.000 --> 00:05.000] text here
                text = output.split("]")[-1].strip()
            else:
                text = output.strip()
            
            return text if text else "Could not transcribe audio"
        else:
            error_msg = result.stderr if result else "Whisper command failed"
            print("Whisper error:", error_msg)
            return "Transcription failed. Please check Whisper installation."
            
    except Exception as e:
        print(f"Error in convert_audio_to_text: {e}")
        return f"Error: {str(e)}"
    
    finally:
        # Cleanup temp files
        for temp_file in [temp_input, temp_output]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

