from flask import Flask, request
import sys

app = Flask(__name__)


@app.route("/alerts", methods=["POST"])
def alerts():
	payload = request.get_json(force=True, silent=True)
	if not payload:
		print("Received empty or invalid JSON payload", file=sys.stdout)
		return "", 200

	alerts = payload.get("alerts", [])
	for a in alerts:
		status = a.get("status")
		labels = a.get("labels", {})
		annotations = a.get("annotations", {})
		alertname = labels.get("alertname") or annotations.get("summary") or "<unknown>"

		print("ALERT RECEIVED", file=sys.stdout)
		print(f"  status: {status}", file=sys.stdout)
		print(f"  alertname: {alertname}", file=sys.stdout)
		print(f"  labels: {labels}", file=sys.stdout)
		print(f"  annotations: {annotations}", file=sys.stdout)
		print("-" * 60, file=sys.stdout)

	return "", 200


@app.route("/health")
def health():
	return "OK", 200


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5001)

