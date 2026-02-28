---
pipeline_tag: image-text-to-text
language:
- multilingual
tags:
- deepseek
- vision-language
- ocr
- custom_code
license: apache-2.0
library_name: transformers
---
<div align="center">
  <img src="https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/logo.svg?raw=true" width="60%" alt="DeepSeek AI" />
</div>
<hr>
<div align="center">
  <a href="https://www.deepseek.com/" target="_blank">
    <img alt="Homepage" src="https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/badge.svg?raw=true" />
  </a>
  <a href="https://huggingface.co/deepseek-ai/DeepSeek-OCR-2" target="_blank">
    <img alt="Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-DeepSeek%20AI-ffc107?color=ffc107&logoColor=white" />
  </a>

</div>

<div align="center">

  <a href="https://discord.gg/Tc7c45Zzu5" target="_blank">
    <img alt="Discord" src="https://img.shields.io/badge/Discord-DeepSeek%20AI-7289da?logo=discord&logoColor=white&color=7289da" />
  </a>
  <a href="https://twitter.com/deepseek_ai" target="_blank">
    <img alt="Twitter Follow" src="https://img.shields.io/badge/Twitter-deepseek_ai-white?logo=x&logoColor=white" />
  </a>

</div>



<p align="center">
  <a href="https://github.com/deepseek-ai/DeepSeek-OCR-2"><b>🌟 Github</b></a> |
  <a href="https://huggingface.co/deepseek-ai/DeepSeek-OCR-2"><b>📥 Model Download</b></a> |
  <a href="https://github.com/deepseek-ai/DeepSeek-OCR-2/blob/main/DeepSeek_OCR2_paper.pdf"><b>📄 Paper Link</b></a> |
  <a href="https://arxiv.org/abs/2601.20552"><b>📄 Arxiv Paper Link</b></a> |
</p>
<h2>
<p align="center">
  <a href="">DeepSeek-OCR 2: Visual Causal Flow</a>
</p>
</h2>
<p align="center">
<img src="assets/fig1.png" style="width: 900px" align=center>
</p>
<p align="center">
<a href="">Explore more human-like visual encoding.</a>       
</p>

## Usage

Inference using Huggingface transformers on NVIDIA GPUs. Requirements tested on python 3.12.9 + CUDA11.8：

```
torch==2.6.0
transformers==4.46.3
tokenizers==0.20.3
einops
addict 
easydict
pip install flash-attn==2.7.3 --no-build-isolation
```

```python
from transformers import AutoModel, AutoTokenizer
import torch
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '0'
model_name = 'deepseek-ai/DeepSeek-OCR-2'

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(model_name, _attn_implementation='flash_attention_2', trust_remote_code=True, use_safetensors=True)
model = model.eval().cuda().to(torch.bfloat16)

# prompt = "<image>\nFree OCR. "
prompt = "<image>\n<|grounding|>Convert the document to markdown. "
image_file = 'your_image.jpg'
output_path = 'your/output/dir'


res = model.infer(tokenizer, prompt=prompt, image_file=image_file, output_path = output_path, base_size = 1024, image_size = 768, crop_mode=True, save_results = True)
```

## vLLM


Refer to [🌟GitHub](https://github.com/deepseek-ai/DeepSeek-OCR-2/) for guidance on model inference acceleration and PDF processing, etc.<!--  -->

## Support-Modes
- Dynamic resolution
  - Default: (0-6)×768×768 + 1×1024×1024 — (0-6)×144 + 256 visual tokens ✅

## Main Prompts
```python
# document: <image>\n<|grounding|>Convert the document to markdown.
# without layouts: <image>\nFree OCR.
```


## Acknowledgement

We would like to thank [DeepSeek-OCR](https://github.com/deepseek-ai/DeepSeek-OCR/), [Vary](https://github.com/Ucas-HaoranWei/Vary/), [GOT-OCR2.0](https://github.com/Ucas-HaoranWei/GOT-OCR2.0/), [MinerU](https://github.com/opendatalab/MinerU), [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) for their valuable models and ideas.

We also appreciate the benchmark [OmniDocBench](https://github.com/opendatalab/OmniDocBench).


## Citation

```bibtex
@article{wei2025deepseek,
  title={DeepSeek-OCR: Contexts Optical Compression},
  author={Wei, Haoran and Sun, Yaofeng and Li, Yukun},
  journal={arXiv preprint arXiv:2510.18234},
  year={2025}
}
@article{wei2026deepseek,
  title={DeepSeek-OCR 2: Visual Causal Flow},
  author={Wei, Haoran and Sun, Yaofeng and Li, Yukun},
  journal={arXiv preprint arXiv:2601.20552},
  year={2026}
}