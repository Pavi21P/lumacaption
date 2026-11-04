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

The supplied dataset may be used as local test input during development; it is not a runtime dependency or part of the public project. If using Flickr8k for separate research or evaluation, consult its own terms and citation requirements.
