# Design decisions

## Independent application, pretrained AI

The source is newly written for LumaCaption. Salesforce BLIP supplies pretrained model weights. Training a new neural network is outside this version's scope. The uploaded video files were inspected to understand the starting point; none are copied, imported, packaged, or required at runtime.

## Windows first

Use Python 3.11–3.13, Tkinter/ttk, Pillow, PyTorch, and Transformers. Native file dialogs and pathlib handle spaces and Unicode in Windows paths. Inference runs on a worker thread, with all Tk updates on the main thread. CPU is the reliable default.

## Local processing

Only model files are downloaded from Hugging Face. Images are opened locally and never submitted to a captioning API. Offline mode uses cached model files only. Exports are user-selected files.

## Honest progress

Record implementation, tests, and remaining limitations in each meaningful commit. Keep future improvements separate. Do not create empty commits, backdate commits, or imply work ran on days it did not.

## Explicit device choice; CPU stays default (LC12)

Offer cpu/cuda as a local runtime preference without changing the saved-session
schema or the fixed CPU evaluation protocol. Preserve the existing CPU environment.
Report the actual device and fallback reason. Retry CUDA out-of-memory once on CPU;
leave other inference errors visible. GPU routing is covered with simulations until
supported hardware is available; no real-GPU performance or compatibility claim.
See [device behavior](DEVICES.md).
