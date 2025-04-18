import gradio as gr
from pathlib import Path
from LatentSync.scripts.inference import main
from omegaconf import OmegaConf
import argparse
from datetime import datetime


class LatentSyncGenerator:
    def __init__(self):
        self.config_path = Path("LatentSync/configs/unet/stage2.yaml")
        self.checkpoint_path = Path("LatentSync/checkpoints/latentsync_unet.pt")

    def process_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str = None,
        guidance_scale: float = 7.5,
        inference_steps: int = 50,
        seed: int = 42,
    ):
        """Process video with LatentSync model"""
        # Create the temp directory if it doesn't exist
        output_dir = Path("./temp")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert paths to absolute Path objects and normalize them
        video_file_path = Path(video_path)
        video_path = video_file_path.absolute().as_posix()
        audio_path = Path(audio_path).absolute().as_posix()

        # Set output path if not provided
        if output_path is None:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"{video_file_path.stem}_{current_time}.mp4")

        # Load and update config
        config = OmegaConf.load(self.config_path)
        config["run"].update({
            "guidance_scale": guidance_scale,
            "inference_steps": inference_steps,
        })

        # Create arguments
        args = create_args(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            inference_steps=inference_steps,
            guidance_scale=guidance_scale,
            seed=seed
        )

        try:
            result = main(
                config=config,
                args=args,
            )
            print("Processing completed successfully.")
            return output_path
        except Exception as e:
            print(f"Error during processing: {str(e)}")
            raise


def create_args(
    video_path: str, audio_path: str, output_path: str, inference_steps: int, guidance_scale: float, seed: int
) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inference_ckpt_path", type=str, required=True)
    parser.add_argument("--video_path", type=str, required=True)
    parser.add_argument("--audio_path", type=str, required=True)
    parser.add_argument("--video_out_path", type=str, required=True)
    parser.add_argument("--inference_steps", type=int, default=20)
    parser.add_argument("--guidance_scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1247)

    return parser.parse_args(
        [
            "--inference_ckpt_path",
            LatentSyncGenerator().checkpoint_path.absolute().as_posix(),
            "--video_path",
            video_path,
            "--audio_path",
            audio_path,
            "--video_out_path",
            output_path,
            "--inference_steps",
            str(inference_steps),
            "--guidance_scale",
            str(guidance_scale),
            "--seed",
            str(seed),
        ]
    )
