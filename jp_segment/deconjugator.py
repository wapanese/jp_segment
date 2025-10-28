from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeconjugationForm:
    text: str
    original_text: str
    tags: tuple[str, ...]
    seen_text: frozenset[str]
    process: tuple[str, ...]


@dataclass
class Rule:
    type: str
    context_rule: str | None
    dec_end: list[str]
    con_end: list[str]
    dec_tag: list[str] | None
    con_tag: list[str] | None
    detail: str


class Deconjugator:
    def __init__(self, rules_path: Path) -> None:
        txt = rules_path.read_text(encoding="utf-8")
        # Allow // comments
        lines = []
        for line in txt.splitlines():
            ls = line.lstrip()
            if ls.startswith("//"):
                continue
            lines.append(line)
        raw = json.loads("\n".join(lines))
        self.rules: list[Rule] = []
        for r in raw:
            self.rules.append(
                Rule(
                    type=r["type"],
                    context_rule=r.get("contextrule"),
                    dec_end=r["dec_end"],
                    con_end=r["con_end"],
                    dec_tag=r.get("dec_tag"),
                    con_tag=r.get("con_tag"),
                    detail=r.get("detail", ""),
                )
            )

    def deconjugate(self, text: str) -> set[DeconjugationForm]:
        processed: set[DeconjugationForm] = set()
        if not text:
            return processed
        novel: set[DeconjugationForm] = {
            DeconjugationForm(text=text, original_text=text, tags=(), seen_text=frozenset(), process=())
        }
        rules = self.rules
        while novel:
            new_novel: set[DeconjugationForm] = set()
            for form in novel:
                if self._skip(form):
                    continue
                for rule in rules:
                    out = self._apply_rule(form, rule)
                    if not out:
                        continue
                    for f in out:
                        if f not in processed and f not in novel and f not in new_novel:
                            new_novel.add(f)
            processed |= novel
            novel = new_novel
        return processed

    @staticmethod
    def _skip(form: DeconjugationForm) -> bool:
        return (
            (not form.text) or (len(form.text) > len(form.original_text) + 10) or (len(form.tags) > len(form.original_text) + 6)
        )

    def _apply_rule(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        t = rule.type
        if t == "stdrule":
            return self._std_rule(form, rule)
        if t == "rewriterule":
            return self._rewrite_rule(form, rule)
        if t == "onlyfinalrule":
            return self._only_final_rule(form, rule)
        if t == "neverfinalrule":
            return self._neverfinal_rule(form, rule)
        if t == "contextrule":
            return self._context_rule(form, rule)
        if t == "substitution":
            return self._substitution(form, rule)
        return None

    def _std_rule(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        if (not rule.detail) and len(form.tags) == 0:
            return None
        outs: set[DeconjugationForm] = set()

        def try_one(dec_end: str, con_end: str, dec_tag: str | None, con_tag: str | None) -> None:
            if not form.text.endswith(con_end):
                return
            if form.tags and (form.tags[-1] != con_tag):
                return
            prefix = form.text[: len(form.text) - len(con_end)]
            new_text = prefix + dec_end
            if new_text == form.original_text:
                return
            nf = self._create_new_form(form, new_text, con_tag, dec_tag, rule.detail)
            outs.add(nf)

        if len(rule.dec_end) == 1:
            try_one(
                rule.dec_end[0],
                rule.con_end[0],
                rule.dec_tag[0] if rule.dec_tag else None,
                rule.con_tag[0] if rule.con_tag else None,
            )
        else:
            for i in range(len(rule.dec_end)):
                try_one(
                    rule.dec_end[i] if i < len(rule.dec_end) else rule.dec_end[0],
                    rule.con_end[i] if i < len(rule.con_end) else rule.con_end[0],
                    (
                        rule.dec_tag[i]
                        if (rule.dec_tag and i < len(rule.dec_tag))
                        else (rule.dec_tag[0] if rule.dec_tag else None)
                    ),
                    (
                        rule.con_tag[i]
                        if (rule.con_tag and i < len(rule.con_tag))
                        else (rule.con_tag[0] if rule.con_tag else None)
                    ),
                )
        return outs or None

    def _substitution(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        if form.process or not form.text:
            return None
        outs: set[DeconjugationForm] = set()

        def apply(con_end: str, dec_end: str):
            if con_end not in form.text:
                return
            new_text = form.text.replace(con_end, dec_end)
            nf = self._create_substitution_form(form, new_text, rule.detail)
            outs.add(nf)

        if len(rule.dec_end) == 1:
            apply(rule.con_end[0], rule.dec_end[0])
        else:
            for i in range(len(rule.dec_end)):
                apply(
                    rule.con_end[i] if i < len(rule.con_end) else rule.con_end[0],
                    rule.dec_end[i] if i < len(rule.dec_end) else rule.dec_end[0],
                )
        return outs or None

    def _rewrite_rule(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        if form.text == rule.con_end[0]:
            return self._std_rule(form, rule)
        return None

    def _only_final_rule(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        if not form.tags:
            return self._std_rule(form, rule)
        return None

    def _neverfinal_rule(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        if form.tags:
            return self._std_rule(form, rule)
        return None

    def _context_rule(self, form: DeconjugationForm, rule: Rule) -> set[DeconjugationForm] | None:
        if rule.context_rule == "v1inftrap" and (form.tags == ("stem-ren",)):
            return None
        if rule.context_rule == "saspecial":
            if not rule.con_end:
                return None
            con_end = rule.con_end[0]
            if not form.text.endswith(con_end):
                return None
            prefix_len = len(form.text) - len(con_end)
            if prefix_len > 0 and form.text[prefix_len - 1 : prefix_len] == "さ":
                return None
        return self._std_rule(form, rule)

    @staticmethod
    def _create_new_form(
        form: DeconjugationForm, new_text: str, con_tag: str | None, dec_tag: str | None, detail: str
    ) -> DeconjugationForm:
        tags = list(form.tags)
        if not tags and con_tag is not None:
            tags.append(con_tag)
        if dec_tag is not None:
            tags.append(dec_tag)
        seen = set(form.seen_text)
        if not seen:
            seen.add(form.text)
        seen.add(new_text)
        process = list(form.process)
        process.append(detail)
        return DeconjugationForm(
            text=new_text, original_text=form.original_text, tags=tuple(tags), seen_text=frozenset(seen), process=tuple(process)
        )

    @staticmethod
    def _create_substitution_form(form: DeconjugationForm, new_text: str, detail: str) -> DeconjugationForm:
        seen = set(form.seen_text)
        if not seen:
            seen.add(form.text)
        seen.add(new_text)
        process = list(form.process)
        process.append(detail)
        return DeconjugationForm(
            text=new_text, original_text=form.original_text, tags=form.tags, seen_text=frozenset(seen), process=tuple(process)
        )
