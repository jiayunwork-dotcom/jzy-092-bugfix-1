"""Flask 接口层：仅以 HTTP/JSON 对外提供动态穿透计算，不附带页面。"""

from flask import Flask, jsonify, request

from . import __version__, batch, pipeline, presets, validation


def create_app() -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.get("/api/v1/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "fixed-bed-breakthrough",
                "version": __version__,
            }
        )

    @app.get("/api/v1/presets/softening")
    def softening_preset():
        """预置软化床参考算例：返回工况参数并当场算出整条曲线。"""
        result = pipeline.run_condition(dict(presets.SOFTENING_BED_CONDITION))
        return jsonify(
            {
                "name": presets.PRESET_NAME,
                "condition": dict(presets.SOFTENING_BED_CONDITION),
                "result": result,
            }
        )

    @app.post("/api/v1/breakthrough/run")
    def run_single():
        """单一工况：整条曲线连同穿透时刻、累计吸附一次算完返回。"""
        try:
            result = pipeline.run_condition(request.get_json(silent=True))
        except validation.ValidationError as exc:
            return _validation_error(exc)
        return jsonify(result)

    @app.post("/api/v1/breakthrough/batch")
    def run_batch_endpoint():
        """批量工况：数据集逐条独立计算，各条结果互不覆盖。"""
        body = request.get_json(silent=True)
        conditions = body.get("runs") if isinstance(body, dict) else None
        try:
            results = batch.run_batch(conditions)
        except validation.ValidationError as exc:
            return _validation_error(exc)
        return jsonify({"count": len(results), "results": results})

    return app


def _validation_error(exc: validation.ValidationError):
    return (
        jsonify({"error": {"message": str(exc), "reasons": exc.reasons}}),
        400,
    )
