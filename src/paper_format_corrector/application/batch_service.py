"""Batch correction service for processing multiple documents.

Handles multi-file processing with progress tracking, error isolation,
and summary report generation as specified in zhinan.md section 3.9.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..infrastructure.converters.file_converter import FileConverter
from ..infrastructure.converters.file_formatter import FormatCorrector
from ..infrastructure.logger import Logger


@dataclass
class BatchJob:
    """Single file batch job"""
    input_path: str
    output_path: str
    template_path: str = ""
    config: dict = field(default_factory=dict)
    score: bool = False
    export_formats: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """Result of a single file processing"""
    input_file: str
    output_file: str
    success: bool
    report: dict = field(default_factory=dict)
    error: str = ""
    processing_time: float = 0.0
    quality_score: float = 0.0


@dataclass
class BatchSummary:
    """Summary of batch processing"""
    total_files: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    avg_quality_score: float = 0.0
    results: list[BatchResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def generate_report(self, fmt: str = "text") -> str:
        """生成格式化的批量处理汇总报告。

        Args:
            fmt: 报告格式 - 'text' (纯文本) / 'markdown' / 'html'
        """
        if fmt == "markdown":
            return self._report_markdown()
        if fmt == "html":
            return self._report_html()
        return self._report_text()

    def _report_text(self) -> str:
        lines = [
            "=" * 60,
            "批量处理汇总报告",
            "=" * 60,
            f"  总文件数:     {self.total_files}",
            f"  成功:         {self.success_count}",
            f"  失败:         {self.failed_count}",
            f"  总耗时:       {self.total_processing_time:.1f}s",
            f"  平均耗时:     {self.avg_processing_time:.1f}s/文件",
        ]
        if self.avg_quality_score > 0:
            lines.append(f"  平均质量评分: {self.avg_quality_score:.1f}/100")

        # Per-file details
        if self.results:
            lines.append("\n" + "-" * 60)
            lines.append("文件详情:")
            lines.append("-" * 60)
            for r in self.results:
                status = "✓" if r.success else "✗"
                score_str = f" 评分:{r.quality_score:.0f}" if r.quality_score > 0 else ""
                time_str = f" {r.processing_time:.1f}s"
                lines.append(f"  {status} {Path(r.input_file).name}{score_str}{time_str}")
                if not r.success and r.error:
                    lines.append(f"    错误: {r.error}")

        if self.errors:
            lines.append("\n" + "-" * 60)
            lines.append("失败详情:")
            lines.append("-" * 60)
            for error in self.errors:
                lines.append(f"  - {error}")

        return "\n".join(lines)

    def _report_markdown(self) -> str:
        lines = [
            "# 批量处理汇总报告\n",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 总文件数 | {self.total_files} |",
            f"| 成功 | {self.success_count} |",
            f"| 失败 | {self.failed_count} |",
            f"| 总耗时 | {self.total_processing_time:.1f}s |",
            f"| 平均耗时 | {self.avg_processing_time:.1f}s/文件 |",
        ]
        if self.avg_quality_score > 0:
            lines.append(f"| 平均质量评分 | {self.avg_quality_score:.1f}/100 |")

        if self.results:
            lines.append("\n## 文件详情\n")
            lines.append("| 状态 | 文件名 | 评分 | 耗时 |")
            lines.append("|------|--------|------|------|")
            for r in self.results:
                status = "✓" if r.success else "✗"
                score = f"{r.quality_score:.0f}" if r.quality_score > 0 else "-"
                name = Path(r.input_file).name
                lines.append(f"| {status} | {name} | {score} | {r.processing_time:.1f}s |")

        return "\n".join(lines)

    def _report_html(self) -> str:
        rows = ""
        for r in self.results:
            status = "✓" if r.success else "✗"
            score = f"{r.quality_score:.0f}" if r.quality_score > 0 else "-"
            name = Path(r.input_file).name
            color = "#2d7d46" if r.success else "#d32f2f"
            rows += f'<tr><td style="color:{color}">{status}</td><td>{name}</td><td>{score}</td><td>{r.processing_time:.1f}s</td></tr>\n'

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>批量处理报告</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
h1 {{ color: #333; border-bottom: 2px solid #2196F3; padding-bottom: 0.5rem; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
th, td {{ padding: 0.5rem 1rem; border: 1px solid #ddd; text-align: left; }}
th {{ background: #f5f5f5; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin: 1rem 0; }}
.stat {{ background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center; }}
.stat .num {{ font-size: 1.5rem; font-weight: bold; color: #2196F3; }}
.stat .label {{ color: #666; font-size: 0.9rem; }}
</style></head><body>
<h1>批量处理汇总报告</h1>
<div class="summary">
  <div class="stat"><div class="num">{self.total_files}</div><div class="label">总文件数</div></div>
  <div class="stat"><div class="num" style="color:#2d7d46">{self.success_count}</div><div class="label">成功</div></div>
  <div class="stat"><div class="num" style="color:#d32f2f">{self.failed_count}</div><div class="label">失败</div></div>
  <div class="stat"><div class="num">{self.total_processing_time:.1f}s</div><div class="label">总耗时</div></div>
  {"<div class='stat'><div class='num'>" + f"{self.avg_quality_score:.1f}" + "</div><div class='label'>平均评分</div></div>" if self.avg_quality_score > 0 else ""}
</div>
<h2>文件详情</h2>
<table><thead><tr><th>状态</th><th>文件名</th><th>评分</th><th>耗时</th></tr></thead>
<tbody>{rows}</tbody></table>
</body></html>"""

    def create_zip(self, zip_path: str | Path) -> Path:
        """Create a zip archive containing all successful output files and reports.

        Args:
            zip_path: Path for the output zip file

        Returns:
            Path to the created zip file
        """
        import zipfile
        zip_path = Path(zip_path)
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            # Add all successful output files
            for result in self.results:
                if result.success and Path(result.output_file).exists():
                    zf.write(result.output_file, Path(result.output_file).name)

            # Add summary reports
            zf.writestr("batch_summary.txt", self.generate_report(fmt="text"))
            zf.writestr("batch_summary.md", self.generate_report(fmt="markdown"))
            zf.writestr("batch_summary.html", self.generate_report(fmt="html"))

        return zip_path


class BatchCorrectionService:
    """Service for batch processing multiple documents."""

    def __init__(self, config: dict[str, Any], log_level: str = "INFO"):
        self.config = config
        self.template_path = config.get("template", {}).get("path", "")
        self.logger = Logger(level=log_level)
        self.converter = FileConverter()

    def process_files(
        self,
        input_files: list[str | Path],
        output_dir: str | Path,
        score: bool = False,
        export_formats: list[str] | None = None,
        max_workers: int | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> BatchSummary:
        """Process multiple files with error isolation and progress tracking.

        Args:
            input_files: List of input file paths
            output_dir: Directory for output files
            score: Whether to compute quality scores
            export_formats: Additional export formats
            max_workers: Max parallel workers (None = auto)
            progress_callback: Callback(current, total, filename)

        Returns:
            BatchSummary with all results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        jobs = self._build_jobs(input_files, output_path, score, export_formats or [])

        if not jobs:
            self.logger.warning("没有找到可处理的文件")
            return BatchSummary()

        summary = BatchSummary(total_files=len(jobs))
        start_time = time.time()

        for idx, job in enumerate(jobs):
            if progress_callback:
                progress_callback(idx + 1, len(jobs), Path(job.input_path).name)

            result = self._process_single_file(job)
            summary.results.append(result)

            if result.success:
                summary.success_count += 1
                if result.quality_score > 0:
                    scores = [r.quality_score for r in summary.results if r.quality_score > 0]
                    summary.avg_quality_score = sum(scores) / len(scores) if scores else 0
            else:
                summary.failed_count += 1
                summary.errors.append(f"{Path(job.input_path).name}: {result.error}")

        summary.total_processing_time = time.time() - start_time
        summary.avg_processing_time = summary.total_processing_time / len(jobs) if jobs else 0

        self._print_summary(summary)
        return summary

    def process_directory(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        score: bool = False,
        export_formats: list[str] | None = None,
        recursive: bool = False,
        max_workers: int | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> BatchSummary:
        """Process all supported files in a directory."""
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise ValueError(f"输入目录不存在: {input_dir}")

        extensions = self.converter.SUPPORTED_INPUT_FORMATS if hasattr(self.converter, 'SUPPORTED_INPUT_FORMATS') else ['.docx', '.doc', '.txt', '.md', '.pdf']
        files: list[Path] = []
        for ext in extensions:
            if recursive:
                files.extend(input_path.rglob(f"*{ext}"))
            else:
                files.extend(input_path.glob(f"*{ext}"))

        files = sorted(files, key=lambda f: f.name)

        if not files:
            self.logger.warning(f"在 {input_dir} 中未找到支持的文档文件")
            return BatchSummary()

        return self.process_files(
            [str(f) for f in files], output_dir, score, export_formats,
            max_workers, progress_callback,
        )

    def _build_jobs(
        self,
        input_files: list[str | Path],
        output_dir: Path,
        score: bool,
        export_formats: list[str],
    ) -> list[BatchJob]:
        jobs: list[BatchJob] = []
        for input_file in input_files:
            input_path = Path(input_file)
            if not input_path.is_file():
                self.logger.warning(f"文件不存在，跳过: {input_file}")
                continue

            processing_file = input_path
            if self.converter.needs_conversion(str(input_path)):
                try:
                    converted = self.converter.convert(str(input_path), str(output_dir))
                    processing_file = Path(converted)
                except Exception as e:
                    self.logger.error(f"格式转换失败 {input_path.name}: {e}")
                    continue

            output_file = str(output_dir / f"formatted_{processing_file.name}")
            jobs.append(BatchJob(
                input_path=str(processing_file),
                output_path=output_file,
                template_path=self.template_path,
                config=self.config,
                score=score,
                export_formats=export_formats,
            ))
        return jobs

    def _process_single_file(self, job: BatchJob) -> BatchResult:
        start = time.time()
        try:
            corrector = FormatCorrector(job.template_path, job.config)
            report = corrector.correct_document(job.input_path, job.output_path)

            quality_score = 0.0
            if job.score:
                try:
                    from ..domain.quality.quality_scorer import QualityScorer
                    scorer = QualityScorer(job.config)
                    total, _, _ = scorer.score(job.output_path)
                    quality_score = total
                    report["quality_score"] = total
                except Exception:
                    pass

            return BatchResult(
                input_file=job.input_path,
                output_file=job.output_path,
                success=True,
                report=report,
                processing_time=time.time() - start,
                quality_score=quality_score,
            )
        except Exception as e:
            return BatchResult(
                input_file=job.input_path,
                output_file=job.output_path,
                success=False,
                error=str(e),
                processing_time=time.time() - start,
            )

    def _print_summary(self, summary: BatchSummary) -> None:
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info("批量处理汇总")
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"  总文件数:   {summary.total_files}")
        self.logger.info(f"  成功:       {summary.success_count}")
        self.logger.info(f"  失败:       {summary.failed_count}")
        self.logger.info(f"  总耗时:     {summary.total_processing_time:.1f}s")
        self.logger.info(f"  平均耗时:   {summary.avg_processing_time:.1f}s/文件")
        if summary.avg_quality_score > 0:
            self.logger.info(f"  平均评分:   {summary.avg_quality_score:.1f}/100")
        if summary.errors:
            self.logger.info("\n  失败详情:")
            for error in summary.errors:
                self.logger.info(f"    - {error}")

    def async_process_files(
        self,
        input_files: list[str | Path],
        output_dir: str | Path,
        score: bool = False,
        export_formats: list[str] | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[str]:
        """异步模式：将每个文件包装为 TaskQueue 任务并提交。

        Args:
            input_files: 待处理文件列表
            output_dir: 输出目录
            score: 是否计算质量评分
            export_formats: 额外导出格式
            progress_callback: 进度回调

        Returns:
            任务 ID 列表
        """
        from ..infrastructure.queue.task_queue import TaskQueue

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        task_queue = TaskQueue()
        task_ids: list[str] = []

        for input_file in input_files:
            input_path = Path(input_file)
            if not input_path.is_file():
                self.logger.warning(f"文件不存在，跳过: {input_file}")
                continue

            task_id = task_queue.submit(
                file_path=str(input_path),
                template_id=self.template_path or None,
                filename=input_path.name,
            )
            task_ids.append(task_id)

        self.logger.info(f"已提交 {len(task_ids)} 个异步任务")
        return task_ids


def process_batch_standalone(args: tuple) -> BatchResult:
    """Standalone function for ProcessPoolExecutor (must be picklable)."""
    input_file, output_file, template_path, config, score = args
    start = time.time()
    try:
        corrector = FormatCorrector(template_path, config)
        report = corrector.correct_document(input_file, output_file)
        quality_score = 0.0
        if score:
            try:
                from ..domain.quality.quality_scorer import QualityScorer
                scorer = QualityScorer(config)
                total, _, _ = scorer.score(output_file)
                quality_score = total
                report["quality_score"] = total
            except Exception:
                pass
        return BatchResult(
            input_file=input_file, output_file=output_file,
            success=True, report=report,
            processing_time=time.time() - start,
            quality_score=quality_score,
        )
    except Exception as e:
        return BatchResult(
            input_file=input_file, output_file=output_file,
            success=False, error=str(e),
            processing_time=time.time() - start,
        )
