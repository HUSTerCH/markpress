from reportlab.pdfbase.pdfmetrics import stringWidth

from markpress.inherited.SafeCJKParagraph import SafeCJKParagraph


class SmartInlineImgParagraph(SafeCJKParagraph):
    def __init__(self, text, style, **kwargs):
        super().__init__(text=text, style=style, **kwargs)

    """
    在 wrap 阶段根据当前行剩余宽度，决定 inline <img> 是否强制换行。
    适用于你的场景：文本里夹多个 <img .../>（公式图）。
    """
    def _estimate_frag_width(self, frag) -> float:
        # img frag：直接用 frag.width
        if getattr(frag, "__tag__", None) == "img":
            return float(getattr(frag, "width", 0.0) or 0.0)

        # 普通文本 frag：用 stringWidth 估算（Paragraph 内部也这么干）
        txt = getattr(frag, "text", "") or ""
        fontName = getattr(frag, "fontName", self.style.fontName)
        fontSize = getattr(frag, "fontSize", self.style.fontSize)

        # 注意：这里按“整段文本”估宽只用于“决定 img 是否换行”的近似游标推进。
        # 真正断行仍由 Paragraph 自己做，所以不会破坏最终排版。
        return float(stringWidth(txt, fontName, fontSize))

    def _inject_br_before_imgs_if_needed(self, availWidth: float) -> bool:
        """
        扫一遍 frags，维护一个近似的“当前行已用宽度 used_w”。
        走到 img 时算 remaining_w，不够就把 img 前面插一个换行 <br/>（通过改 raw text 重建）。
        返回：是否发生过注入（注入则需要重建 Paragraph）。
        """
        # Paragraph 的原始 XML 在 self.text（reportlab 叫 text，实际是带标签的标记串）
        raw = getattr(self, "text", None)
        if not raw:
            return False

        # 关键：我们不能直接改 self.frags（内部状态很复杂、版本差异大）
        # 最稳：改 raw xml，在每个 <img .../> 前根据估算决定插入 <br/>
        # 做法：先用 Paragraph 自己解析出 frags，再按 frags 游标推进，
        #       同时用一个简单的“定位策略”在 raw 里给对应 img 插 <br/>.
        #
        # 这里采用保守策略：只在 raw 中出现的 "<img " 前注入。
        #
        # 限制：如果同一段里有非常多 img，且 raw 被 Paragraph 规范化后格式变了，
        #       需要更严格的 tokenizer；但你当前是公式渲染器生成的标准 <img .../>，通常稳定。

        used_w = 0.0
        changed = False
        out = []
        i = 0
        n = len(raw)

        while i < n:
            # 找下一个 <img
            j = raw.find("<img", i)
            if j < 0:
                out.append(raw[i:])
                break

            # 先把 img 之前的文本吐出去
            before = raw[i:j]
            out.append(before)

            # 估算 before 对当前行 used_w 的推进（粗略）
            # 粗略够用：我们只需要判断 img 是否“明显塞不下”
            if before:
                # 简化：把标签去掉，只估纯文本（避免把 <font> 等当字符）
                # 你已经在上游生成的是相对干净的 xml，这里不做复杂 HTML 解析
                plain = []
                in_tag = False
                for ch in before:
                    if ch == "<":
                        in_tag = True
                    elif ch == ">":
                        in_tag = False
                    elif not in_tag:
                        plain.append(ch)
                plain = "".join(plain)
                if plain:
                    used_w += stringWidth(plain, self.style.fontName, self.style.fontSize)

            # 抓出这个 img 标签整体
            k = raw.find("/>", j)
            if k < 0:
                # 非法 img，放弃
                out.append(raw[j:])
                break
            img_tag = raw[j:k + 2]

            # 从 img_tag 提取 width=".."
            img_w = 0.0
            wpos = img_tag.find('width="')
            if wpos >= 0:
                wpos += len('width="')
                wend = img_tag.find('"', wpos)
                if wend > wpos:
                    try:
                        img_w = float(img_tag[wpos:wend])
                    except:
                        img_w = 0.0

            remaining = (availWidth - used_w % availWidth) - 15 # 留下一定的安全阈值
            # print(f"插{img_tag}时availWidth={availWidth},安全阈值={15},used_w={used_w},还剩：", remaining)
            if img_w > 0 and 0 < remaining < img_w:
                # print(f"在{img_tag}处需要换行，因为remaining还剩{remaining},插入<br/>")
                # 强制换行：插入 <br/>
                out.append("<br/>")
                used_w = availWidth
                changed = True

            out.append(img_tag)
            used_w += img_w
            i = k + 2

        if changed:
            self._smart_new_text = "".join(out).replace("<br/><br/>", "<br/>")
        return changed

    def wrap(self, availWidth, availHeight):
        if self._inject_br_before_imgs_if_needed(availWidth):
            new_text = self._smart_new_text
            rebuilt = self.__class__(new_text, self.style, bulletText=getattr(self, "bulletText", None))
            self.__dict__.update(rebuilt.__dict__)

        return super().wrap(availWidth, availHeight)