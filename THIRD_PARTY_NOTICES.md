# Third-party notices

LumaCaption's MIT license covers its original application code only.

## Pretrained model

- Model: [Salesforce/blip-image-captioning-base](https://huggingface.co/Salesforce/blip-image-captioning-base)
- Pinned revision: `82a37760796d32b1411fe092ab5d4e227313294b`
- Upstream model card identifies its license as BSD-3-Clause.
- [BLIP upstream license](https://github.com/salesforce/BLIP/blob/main/LICENSE.txt)
- Research: Junnan Li, Dongxu Li, Caiming Xiong, Steven Hoi. [BLIP: Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation](https://arxiv.org/abs/2201.12086), 2022.

Model weights are downloaded directly from Hugging Face at runtime and are not redistributed in this repository. LumaCaption does not claim ownership of the model, its training data, or its architecture. No endorsement by Salesforce is implied.

## Runtime dependencies

Python/Tkinter, Pillow, PyTorch, Transformers, Hugging Face Hub, truststore, and their dependencies retain their upstream licenses. Installed packages include their license metadata. The pinned dependency snapshot is in requirements-lock.txt.

## Tutorial provenance

The starting concept was an image-captioning tutorial at https://www.youtube.com/watch?v=3H1x8SDYgvQ. Supplied scripts were reviewed to identify portability and usability issues. This application contains no copied tutorial implementation, original tutorial files, Flickr8k images/captions, or generated tutorial model files.

The supplied dataset may be used as local test input during development; it is not a runtime dependency or part of the public project. The [Flickr8k publisher's terms](https://hockenmaier.cs.illinois.edu/Framing_Image_Description/KCCA.html) provide the material for non-commercial research and educational use; original image copyrights remain with their owners. No dataset redistribution rights are granted by LumaCaption's license. See the [local evaluation protocol](docs/EVALUATION.md) for citation, selection, and storage requirements.

## Windows executable builds

The portable build bundles CPython, Tcl/Tk, and application dependencies. The build script copies installed license/notice texts into licenses/ with a versioned inventory, including Python's license and Tcl/Tk notices. The Tcl 8.6.12 notice is retained verbatim from the [official Tcl source tag](https://github.com/tcltk/tcl/blob/core-8-6-12/license.terms) in packaging/licenses/Tcl-license.terms. Runtime packages, their bundled components, and build tools retain their own licenses; the inventory includes build-tool notices as well.

[PyInstaller's license and distribution exception](https://pyinstaller.org/en/stable/license.html) permit bundling applications while preserving dependency license obligations. We keep its available notices in the build inventory. Model weights and user data are excluded from the executable folder. The folder build is unsigned, and no clean-machine certification or bit-for-bit reproducibility is claimed.
