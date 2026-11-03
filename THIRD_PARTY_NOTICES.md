# Third-party notices

## Model licenses

The MIT license applies to Director’s Cut's application code, not third-party models. Running models locally does not waive their terms. MiniMax H3 and H3-based derivatives have territorial, commercial and acceptable-use conditions. See [Model licenses](docs/model-licenses.md) and the [complete bundled H3 agreement](docs/MiniMax-H3-LICENSE.txt). Omni/community conversions do not remove the underlying H3 conditions. These notices do not certify deployment or distribution compliance.

Category icons are from [Lucide](https://lucide.dev), bundled locally in
`web/assets/icons/lucide`. Their ISC license and applicable Feather MIT notices
are retained in that directory's `LICENSE` file.

## Retained upstream license notice

The following Comfy Org MIT notice is retained from the initial prototype materials. It is a license notice, not a claim that Director’s Cut uses another studio application as its implementation.

MIT License

Copyright (c) 2026 Comfy Org

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
# Optional MCP bridge and prompt references

The optional MCP bridge uses the official Model Context Protocol Python SDK
(MIT), installed separately via `requirements-mcp.txt`:
https://github.com/modelcontextprotocol/python-sdk/tree/v1.x

Qwen prompt reference documents are from kjranyone/qwen-image-2.1-prompt-guide
(MIT). The original notice is retained in
`docs/prompt-guides/QWEN-GUIDE-LICENSE.txt`; source URLs and checksums are in
`docs/prompt-guides/sources.json`.

MiniMax H3 prompt documents are from the official MiniMaxAI/MiniMax-H3
repository. Attribution/source URLs are in the same manifest. Their presence
does not change the separate upstream model/community license terms.


# CPU scene detection

PySceneDetect0.7.1 (https://github.com/Breakthrough/PySceneDetect) is used for local scene boundary detection. Its BSD3-Clause notice follows. OpenCV is installed as its decoding dependency and retains its own upstream notices.

BSD 3-Clause License

Copyright (C) 2014, Brandon Castellano

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
