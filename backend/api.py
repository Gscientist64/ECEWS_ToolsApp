# backend/api.py
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from extensions import db
from models import Users, Tool, ToolCategory, Request as RequestModel, RequestedTool
import csv, io
from sqlalchemy.orm import joinedload
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')

# --------- Helpers ---------
def tool_to_dict(t: Tool):
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description or "",
        "quantity": getattr(t, "quantity", 0),  # quantity in stock
        "category": t.category.name if getattr(t, "category", None) else ""
    }

# --------- Health ---------
@api_bp.route("/ping")
def ping():
    return jsonify({"ok": True}), 200

# --------- Auth ---------
@api_bp.route('/signup', methods=['POST'])
def api_signup():
    from werkzeug.security import generate_password_hash
    import os

    data = request.get_json(force=True) or {}
    username   = (data.get('username')   or '').strip()
    password   = (data.get('password')   or '').strip()
    first_name = (data.get('first_name') or '').strip()
    email      = (data.get('email')      or '').strip()
    role       = (data.get('role')       or 'user').strip().lower()   # 'admin' | 'user'
    facility   = (data.get('facility')   or '').strip()
    admin_key  = (data.get('admin_key')  or '').strip()

    if not username or not password or not first_name:
        return jsonify({"error": "username, password, first_name required"}), 400
    if not facility:
        return jsonify({"error": "facility required"}), 400
    if Users.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409

    # ✅ Require admin key if registering as admin
    if role == 'admin':
        expected = os.getenv('ADMIN_SIGNUP_KEY', 'temitope999')
        if admin_key != expected:
            return jsonify({
                "error": "Invalid admin key. Please contact the State HiFRAVL team for admin privilege."
            }), 403

    user = Users(
        username=username,
        password=generate_password_hash(password),
        first_name=first_name,
        email=email
    )
    # Support either 'role' or 'roles' column in your model
    if hasattr(user, 'role'):
        user.role = role
    if hasattr(user, 'roles'):
        user.roles = role
    if hasattr(user, 'facility'):
        user.facility = facility

    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "signup ok"}), 201

@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True) or {}
    user = Users.query.filter_by(username=data.get('username')).first()
    if not user:
        return jsonify({"error": "invalid credentials"}), 401

    from werkzeug.security import check_password_hash
    ok = (user.password == data.get('password')) or check_password_hash(user.password, data.get('password'))
    if not ok:
        return jsonify({"error": "invalid credentials"}), 401

    login_user(user)
    return jsonify({
        "message": "ok",
        "user": {"id": user.id, "name": user.first_name, "role": getattr(user, "role", getattr(user, "roles", "user"))}
    }), 200

@api_bp.route('/me')
def me():
    if not current_user.is_authenticated:
        return jsonify(None), 200
    role = getattr(current_user, "role", getattr(current_user, "roles", "user"))
    return jsonify({
        "id": current_user.id,
        "username": getattr(current_user, "username", None),
        "first_name": getattr(current_user, "first_name", None),
        "name": getattr(current_user, "first_name", None),   # keep 'name' for existing UI
        "email": getattr(current_user, "email", None),
        "facility": getattr(current_user, "facility", None),
        "role": role
    }), 200


@api_bp.route('/logout', methods=['POST'])
def api_logout():
    logout_user()
    return jsonify({"message": "ok"}), 200

# --------- Tools ---------
@api_bp.route('/tools')
@login_required
def list_tools():
    q = request.args.get('q', '').lower()
    query = Tool.query.order_by(Tool.name.asc())
    if q:
        query = query.filter(Tool.name.ilike(f"%{q}%"))
    items = [tool_to_dict(t) for t in query.all()]
    return jsonify(items), 200

@api_bp.route('/tools', methods=['POST'])
@login_required
def create_tool():
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "name required"}), 400

    cat_name = (data.get('category') or '').strip()
    category = ToolCategory.query.filter_by(name=cat_name).first() if cat_name else None

    t = Tool(
        name=name,
        description=(data.get('description') or '').strip(),
        category=category,
        quantity=int(data.get('quantity') or 0),
    )

    db.session.add(t)
    db.session.commit()
    return jsonify(tool_to_dict(t)), 201

@api_bp.route('/tools/<int:tid>', methods=['PUT'])
@login_required
def update_tool(tid):
    t = Tool.query.get_or_404(tid)
    data = request.get_json(force=True) or {}

    if 'name' in data: t.name = (data.get('name') or '').strip()
    if 'description' in data: t.description = (data.get('description') or '').strip()
    if 'quantity' in data:
        try:
            t.quantity = max(0, int(data.get('quantity')))
        except Exception:
            return jsonify({"error": "quantity must be integer"}), 400

    if data.get('category') is not None:
        cat_name = (data.get('category') or '').strip()
        t.category = ToolCategory.query.filter_by(name=cat_name).first() if cat_name else None

    db.session.commit()
    return jsonify(tool_to_dict(t)), 200

@api_bp.route('/tools/<int:tid>', methods=['DELETE'])
@login_required
def delete_tool(tid):
    data = request.get_json(silent=True) or {}
    pwd = data.get('password') if isinstance(data, dict) else None
    if pwd != "ecews@2022":
        return jsonify({"error": "Invalid admin password"}), 403

    t = Tool.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200

@api_bp.route('/tools/<int:tid>/checkout', methods=['POST'])
@login_required
def checkout_tool(tid):
    t = Tool.query.get_or_404(tid)
    data = request.get_json(force=True) or {}
    assignee = data.get('assignee', '')
    if hasattr(t, 'status'):
        t.status = 'in_use'
    if hasattr(t, 'assignee'):
        t.assignee = assignee
    db.session.commit()
    return jsonify(tool_to_dict(t)), 200

@api_bp.route('/tools/<int:tid>/checkin', methods=['POST'])
@login_required
def checkin_tool(tid):
    t = Tool.query.get_or_404(tid)
    if hasattr(t, 'status'):
        t.status = 'available'
    if hasattr(t, 'assignee'):
        t.assignee = ''
    db.session.commit()
    return jsonify(tool_to_dict(t)), 200

@api_bp.route('/tools/<int:tid>/logs', methods=['GET'])
@login_required
def tool_logs(tid):
    tool = Tool.query.get_or_404(tid)
    # Most recent first
    logs = (
        tool.usage_records  # relationship from ToolUsage
    )
    out = []
    for u in sorted(logs, key=lambda x: x.date_used or datetime.min, reverse=True):
        out.append({
            "id": u.id,
            "tool_id": u.tool_id,
            "quantity": u.quantity_used,
            "date": (u.date_used.isoformat() if u.date_used else None),
            # facility via user
            "facility": getattr(u.user, "facility", ""),
            "user_name": getattr(u.user, "first_name", getattr(u.user, "username", "")) if u.user else "",
        })
    return jsonify(out), 200


@api_bp.route('/tools/export')
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'category', 'tag', 'serial', 'status', 'assignee', 'location'])
    for t in Tool.query.all():
        writer.writerow([
            t.id, t.name, (t.category.name if t.category else ''),
            getattr(t, 'tag', ''), getattr(t, 'serial', ''), getattr(t, 'status', 'available'),
            getattr(t, 'assignee', ''), getattr(t, 'location', '')
        ])
    output.seek(0)
    return output.getvalue(), 200, {'Content-Type': 'text/csv; charset=utf-8'}

@api_bp.route('/tools/import', methods=['POST'])
@login_required
def import_csv():
    if 'file' not in request.files:
        return jsonify({"error": "file required"}), 400
    f = request.files['file']
    stream = io.StringIO(f.stream.read().decode('utf-8'))
    reader = csv.DictReader(stream)
    created = 0
    for row in reader:
        name = row.get('name') or row.get('Name')
        if not name:
            continue
        catname = row.get('category') or row.get('Category')
        category = ToolCategory.query.filter_by(name=catname).first() if catname else None
        t = Tool(name=name, description=row.get('description', ''), category=category)
        for k in ['tag', 'serial', 'status', 'assignee', 'location']:
            if hasattr(t, k) and row.get(k):
                setattr(t, k, row.get(k))
        db.session.add(t)
        created += 1
    db.session.commit()
    return jsonify({"created": created}), 200

# --------- Meta ---------
@api_bp.route('/categories')
@login_required
def categories():
    cats = ToolCategory.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in cats]), 200

@api_bp.route('/users')
@login_required
def users():
    rows = Users.query.all()
    out = []
    for u in rows:
        role = getattr(u, "role", getattr(u, "roles", "user"))
        out.append({
            "id": u.id,
            "name": getattr(u, "first_name", ""),
            "username": getattr(u, "username", ""),
            "email": getattr(u, "email", ""),
            "facility": getattr(u, "facility", ""),
            "role": role
        })
    return jsonify(out), 200

# --------- Catalog (single route; no duplicates) ---------
@api_bp.route("/catalog", methods=['GET'])
def catalog():
    """
    Returns categories with their tools (used by dashboard and request UI).
    Public in dev; can be protected if you prefer.
    """
    cats = ToolCategory.query.options(joinedload(ToolCategory.tools)).order_by(ToolCategory.name.asc()).all()
    data = [{
        "id": c.id,
        "category": c.name,
        "tools": [{"id": t.id, "name": t.name, "description": t.description or ""} for t in (c.tools or [])]
    } for c in cats]
    return jsonify(data), 200

# --------- Requests (explicit auth checks to always return JSON) ---------
@api_bp.route("/requests", methods=["POST"])
def create_request():
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json(force=True) or {}
        items = data.get("items") or []
        if not items or not isinstance(items, list):
            return jsonify({"error": "items array required"}), 400

        valid = []
        for it in items:
            try:
                tid = int(it.get("tool_id"))
                qty = int(it.get("quantity"))
            except Exception:
                return jsonify({"error": "tool_id and quantity must be integers"}), 400
            if qty <= 0:
                return jsonify({"error": "quantity must be > 0"}), 400
            tool = Tool.query.get(tid)
            if not tool:
                return jsonify({"error": f"tool_id {tid} not found"}), 404
            valid.append((tool, qty))

        req = RequestModel(user_id=current_user.id, status="Pending")
        db.session.add(req)
        db.session.flush()  # get req.id

        for tool, qty in valid:
            db.session.add(RequestedTool(
                request_id=req.id, tool_id=tool.id, quantity=qty, status="Pending"
            ))

        db.session.commit()
        return jsonify({"message": "request created", "request_id": req.id}), 201
    except Exception:
        current_app.logger.exception("create_request failed")
        return jsonify({"error": "Failed to create request"}), 500

@api_bp.route("/requests", methods=["GET"])
def my_requests():
    # Always return JSON (even if not logged in)
    if not current_user.is_authenticated:
        return jsonify([]), 200

    try:
        q = (
            RequestModel.query
            .options(joinedload(RequestModel.requested_tools).joinedload(RequestedTool.tool))
            .filter_by(user_id=current_user.id)
            .order_by(RequestModel.date_requested.desc())
        )

        def req_to_json(r):
            try:
                ts = r.date_requested.isoformat() if getattr(r, "date_requested", None) else None
            except Exception:
                ts = None
            return {
                "id": r.id,
                "status": r.status,
                "date_requested": ts,
                "date_approved": (getattr(r, "date_approved", None).isoformat() if getattr(r, "date_approved", None) else None),
                "date_rejected": (getattr(r, "date_rejected", None).isoformat() if getattr(r, "date_rejected", None) else None),
                "approved_by": {
                    "id": getattr(r, "approved_by_id", None),
                    "name": (getattr(getattr(r, "approved_by", None), "first_name", None) if getattr(r, "approved_by", None) else None)
                } if hasattr(r, "approved_by_id") else None,
                "lines": [{
                    "id": rt.id,
                    "tool_id": rt.tool_id,
                    "tool_name": (rt.tool.name if getattr(rt, "tool", None) else ""),
                    "quantity": rt.quantity,
                    "status": rt.status,
                    "in_stock": (getattr(rt.tool, "quantity", 0) if getattr(rt, "tool", None) else 0)
                } for rt in (r.requested_tools or [])]
            }

        data = [req_to_json(r) for r in q.all()]
        return jsonify(data), 200

    except Exception:
        current_app.logger.exception("my_requests failed")
        return jsonify({"error": "Failed to fetch requests"}), 500


# ---------- Admin-only helpers ----------
def _is_admin_user(u):
    # supports either 'role' or 'roles' column
    role = getattr(u, "role", getattr(u, "roles", "user"))
    return (role or "").lower() == "admin"

def _admin_required_json():
    return jsonify({"error": "Forbidden: admin only"}), 403

# ---------- Admin: list requests (optionally filter by status) ----------
@api_bp.route("/admin/requests", methods=["GET"])
def admin_list_requests():
    try:
        if not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized"}), 401
        role = getattr(current_user, "role", getattr(current_user, "roles", "user"))
        if (role or "").lower() != "admin":
            return jsonify({"error": "Forbidden: admin only"}), 403

        status = (request.args.get("status") or "").strip()
        allowed = {"", "Pending", "Approved", "Rejected"}
        if status not in allowed:
            status = ""

        q = RequestModel.query.options(
            joinedload(RequestModel.user),
            joinedload(RequestModel.requested_tools).joinedload(RequestedTool.tool),
        )
        if status:
            q = q.filter(RequestModel.status == status)
        q = q.order_by(RequestModel.date_requested.desc())

        def req_to_json(r):
            return {
                "id": r.id,
                "status": r.status,
                "date_requested": (r.date_requested.isoformat() if getattr(r, "date_requested", None) else None),
                "date_approved": (r.date_approved.isoformat() if getattr(r, "date_approved", None) else None),
                "date_rejected": (getattr(r, "date_rejected", None).isoformat()
                                  if getattr(r, "date_rejected", None) else None),
                "approved_by": (
                    {
                        "id": r.approved_by_id,
                        "name": getattr(getattr(r, "approved_by_user", None), "first_name", None),
                    }
                    if hasattr(r, "approved_by_id") and getattr(r, "approved_by_id", None)
                    else None
                ),
                "user": {
                    "id": r.user.id if r.user else None,
                    "name": r.user.first_name if r.user else "",
                    "username": getattr(r.user, "username", "") if r.user else "",
                    "facility": getattr(r.user, "facility", "") if r.user else "",
                    "email": getattr(r.user, "email", "") if r.user else "",
                },
                "lines": [
                    {
                        "id": ln.id,
                        "tool_id": ln.tool_id,
                        "tool_name": (ln.tool.name if ln.tool else ""),
                        "quantity": ln.quantity,
                        "status": ln.status,
                        # 👉 real current stock from Tool.quantity
                        "in_stock": (getattr(ln.tool, "quantity", 0) or 0),
                    }
                    for ln in (r.requested_tools or [])
                ],
            }

        data = [req_to_json(r) for r in q.all()]
        return jsonify(data), 200

    except Exception:
        current_app.logger.exception("admin_list_requests failed")
        return jsonify({"error": "Failed to load admin requests"}), 500
        
# ---------- Admin: approve a whole request ----------
@api_bp.route("/admin/requests/<int:req_id>/approve", methods=["POST"])
def admin_approve_request(req_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    role = getattr(current_user, "role", getattr(current_user, "roles", "user"))
    if (role or "").lower() != "admin":
        return jsonify({"error": "Forbidden: admin only"}), 403

    r = RequestModel.query.options(joinedload(RequestModel.requested_tools).joinedload(RequestedTool.tool)).get(req_id)
    if not r:
        return jsonify({"error": "Request not found"}), 404

    # Only pending can be approved
    if (r.status or "").lower() != "pending":
        return jsonify({"error": "Only pending requests can be approved"}), 400

    # 1) Validate
    for ln in (r.requested_tools or []):
        tool = ln.tool
        if not tool:
            return jsonify({"error": f"Tool for line {ln.id} not found"}), 404
        in_stock = (getattr(tool, "quantity", 0) or 0)
        if ln.quantity > in_stock:
            return jsonify({
                "error": f"Insufficient stock for '{tool.name}'. Requested {ln.quantity}, in stock {in_stock}. "
                         "Edit quantity to match stock before approval."
            }), 400

    # 2) Deduct and approve
    for ln in (r.requested_tools or []):
        tool = ln.tool
        tool.quantity = (tool.quantity or 0) - ln.quantity
        ln.status = "Approved"
        db.session.add(tool)

    r.status = "Approved"
    if hasattr(r, "date_approved"):
        from datetime import datetime as _dt
        r.date_approved = _dt.utcnow()
    # optional: who approved
    if hasattr(r, "approved_by_id"):
        r.approved_by_id = current_user.id

    db.session.commit()
    return jsonify({"message": "approved"}), 200

@api_bp.route("/admin/requests/<int:req_id>/reject", methods=["POST"])
def admin_reject_request(req_id):
    if not current_user.is_authenticated or not _is_admin_user(current_user):
        return _admin_required_json()

    r = RequestModel.query.options(joinedload(RequestModel.requested_tools)).get(req_id)
    if not r:
        return jsonify({"error": "Request not found"}), 404

    r.status = "Rejected"
    r.date_rejected = datetime.utcnow()
    # Only set approver if the model has the column/relationship
    if hasattr(r, "approved_by_id"):
        r.approved_by_id = current_user.id

    for ln in r.requested_tools or []:
        ln.status = "Rejected"

    db.session.commit()
    return jsonify({"message": "rejected"}), 200

# ---------- Admin: edit a pending request (update line quantities/status) ----------
@api_bp.route("/admin/requests/<int:req_id>", methods=["PUT"])
def admin_edit_request(req_id):
    if not current_user.is_authenticated or not _is_admin_user(current_user):
        return _admin_required_json()

    r = RequestModel.query.options(joinedload(RequestModel.requested_tools)).get(req_id)
    if not r:
        return jsonify({"error": "Request not found"}), 404
    if (r.status or "").lower() != "pending":
        return jsonify({"error": "Only pending requests can be edited"}), 400

    data = request.get_json(force=True) or {}
    lines = data.get("lines") or []
    if not isinstance(lines, list):
        return jsonify({"error": "lines must be a list"}), 400

    # index existing lines
    line_map = {ln.id: ln for ln in (r.requested_tools or [])}
    for patch in lines:
        lid = patch.get("id")
        if lid not in line_map:
            return jsonify({"error": f"line id {lid} not found on this request"}), 404
        ln = line_map[lid]
        if patch.get("quantity") is not None:
            try:
                qv = int(patch.get("quantity"))
            except Exception:
                return jsonify({"error": "quantity must be integer"}), 400
            if qv <= 0:
                return jsonify({"error": "quantity must be > 0"}), 400
            ln.quantity = qv
        if patch.get("status") is not None:
            ln.status = str(patch.get("status"))

    db.session.commit()
    return jsonify({"message": "updated"}), 200

# ---------- Admin: delete a pending request ----------
@api_bp.route("/admin/requests/<int:req_id>", methods=["DELETE"])
def admin_delete_request(req_id):
    if not current_user.is_authenticated or not _is_admin_user(current_user):
        return _admin_required_json()

    r = RequestModel.query.get(req_id)
    if not r:
        return jsonify({"error": "Request not found"}), 404
    if (r.status or "").lower() != "pending":
        return jsonify({"error": "Only pending requests can be deleted"}), 400

    # cascade should remove requested_tools because of relationship; else delete manually
    db.session.delete(r)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200
