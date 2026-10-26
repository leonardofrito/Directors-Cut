# Design reference

Category icons are from [Lucide](https://lucide.dev), bundled locally in
`web/assets/icons/lucide`. Their ISC license and applicable Feather MIT notices
are retained in that directory's `LICENSE` file.

Director's Cut uses [Comfy's hosted Cinematic Studio](https://comfy.org/hub/apps/cinematic-studio/) as its visual reference. The current interface uses our own implementation, layout markup and clapperboard mark. The initial prototype adapted the palette and selected styling conventions from the MIT-licensed [Comfy Cinematic Studio repository](https://github.com/Comfy-Org/comfy-cinematic-studio); its notice is retained below. Director's Cut is an independent project.

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

