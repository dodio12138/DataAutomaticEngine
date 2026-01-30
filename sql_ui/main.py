import os
import re
from typing import List, Tuple, Optional, Dict, Any
import csv
import io
import datetime
import importlib.util

import psycopg2
from psycopg2 import sql
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware


MAX_ROWS = 200
FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "alter",
    "drop",
    "truncate",
    "create",
    "grant",
    "revoke",
    "comment",
    "copy",
}


def get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def parse_optional_date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_readonly_sql(sql: str) -> Tuple[bool, str, str]:
    raw = sql.strip()
    if not raw:
        return False, "SQL 不能为空", ""

    parts = [p.strip() for p in raw.split(";") if p.strip()]
    if len(parts) != 1:
        return False, "只允许单条 SQL 语句", ""

    stmt = parts[0]
    lower = re.sub(r"\s+", " ", stmt).lower()

    if not (lower.startswith("select ") or lower.startswith("with ")):
        return False, "仅允许 SELECT / WITH 查询", ""

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lower):
            return False, f"包含禁止关键字: {kw}", ""

    return True, "", stmt


def get_db_conn():
    return psycopg2.connect(
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
    )


def run_query(sql: str, params: Tuple = ()) -> Tuple[List[str], List[Tuple], bool]:
    return run_query_with_limit(sql, params, MAX_ROWS)


def run_query_with_limit(sql: str, params: Tuple, limit: int) -> Tuple[List[str], List[Tuple], bool]:
    fetch_limit = max(min(limit, MAX_ROWS), 1)
    with get_db_conn() as conn:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return [], [], False
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchmany(fetch_limit + 1)
            has_more = len(rows) > fetch_limit
            return columns, rows[:fetch_limit], has_more


def get_relation_columns(name: str) -> List[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
    """
    columns, rows, _ = run_query(sql, (name,))
    return [row[0] for row in rows]


def clamp_page(value: Optional[str]) -> int:
    try:
        page = int(value or 1)
        return max(page, 1)
    except ValueError:
        return 1


def clamp_limit(value: Optional[str]) -> int:
    try:
        limit = int(value or 50)
        return min(max(limit, 1), MAX_ROWS)
    except ValueError:
        return 50


def build_csv_response(filename: str, columns: List[str], rows: List[Tuple]):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)
    content = output.getvalue()
    output.close()
    response = HTMLResponse(content, media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def load_store_codes() -> List[str]:
    path = os.getenv("STORE_CONFIG_PATH", "/app/crawler/store_config.py")
    if not os.path.exists(path):
        return []
    spec = importlib.util.spec_from_file_location("store_config", path)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store_code_map = getattr(module, "store_code_map", {})
    if isinstance(store_code_map, dict):
        return sorted(store_code_map.keys())
    return []


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=get_env("SQL_UI_SECRET_KEY", "change_me"))

templates = Jinja2Templates(directory="templates")


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("user"))


def is_superuser(request: Request) -> bool:
    return request.session.get("role") == "superuser"


def audit_log_path() -> str:
    log_dir = os.getenv("SQL_UI_LOG_DIR", "/app/logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "audit.log")


def log_audit(request: Request, action: str, detail: str = ""):
    try:
        username = request.session.get("user", "-")
        role = request.session.get("role", "-")
        ip = request.client.host if request.client else "-"
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts}\t{ip}\t{username}\t{role}\t{action}\t{detail}\n"
        with open(audit_log_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def render_dashboard(request: Request, context: Optional[Dict[str, Any]] = None):
    try:
        table_columns, table_rows, _ = run_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
        )
        view_columns, view_rows, _ = run_query(
            """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
        )
        tables = [row[0] for row in table_rows]
        views = [row[0] for row in view_rows]
    except Exception:
        tables = []
        views = []

    base = {
        "request": request,
        "results": {},
        "errors": {},
        "has_more": {},
        "form": {},
        "tables": tables,
        "views": views,
        "platforms": ["panda", "deliveroo"],
        "store_codes": load_store_codes(),
        "active_result": None,
        "active_title": "",
        "pt_columns": [],
        "pv_columns": [],
        "total_count": None,
        "total_pages": None,
        "page_size": None,
        "current_page": None,
        "is_superuser": is_superuser(request),
        "audit_lines": [],
    }
    if context:
        base.update(context)
    return templates.TemplateResponse("index.html", base)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    expected_user = get_env("SQL_UI_USERNAME", "admin")
    expected_pass = get_env("SQL_UI_PASSWORD", "change_me")
    super_user = get_env("SQL_UI_SUPER_USERNAME", "superadmin")
    super_pass = get_env("SQL_UI_SUPER_PASSWORD", "change_me_super")
    if username == super_user and password == super_pass:
        request.session["user"] = username
        request.session["role"] = "superuser"
        log_audit(request, "login", "success")
        return RedirectResponse(url="/", status_code=303)
    if username == expected_user and password == expected_pass:
        request.session["user"] = username
        request.session["role"] = "user"
        log_audit(request, "login", "success")
        return RedirectResponse(url="/", status_code=303)
    log_audit(request, "login", "failed")
    return templates.TemplateResponse("login.html", {"request": request, "error": "账号或密码错误"})


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return render_dashboard(request)


@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request, page: Optional[str] = None, limit: Optional[str] = None):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    if not is_superuser(request):
        return RedirectResponse(url="/", status_code=303)

    try:
        page_value = clamp_page(page)
        limit_value = clamp_limit(limit)
        with open(audit_log_path(), "r", encoding="utf-8") as f:
            lines = [line for line in f.readlines() if line.strip()]
        total_count = len(lines)
        total_pages = max((total_count + limit_value - 1) // limit_value, 1)
        page_value = min(page_value, total_pages)
        start = (page_value - 1) * limit_value
        end = start + limit_value
        page_lines = lines[start:end]
        audit_lines = [line.strip().split("\t") for line in page_lines]
        next_page = page_value + 1 if page_value < total_pages else None
        prev_page = page_value - 1 if page_value > 1 else None
    except Exception:
        audit_lines = []
        total_count = 0
        total_pages = 1
        page_value = 1
        limit_value = 50
        next_page = None
        prev_page = None

    return render_dashboard(
        request,
        {
            "active_result": "audit",
            "active_title": "访问审计日志（最近 200 条）",
            "audit_lines": audit_lines,
            "total_count": total_count,
            "total_pages": total_pages,
            "page_size": limit_value,
            "current_page": page_value,
            "form": {
                "audit_limit": str(limit_value),
                "pager_prev_action": "/audit" if prev_page else "",
                "pager_prev_fields": {
                    "page": str(prev_page) if prev_page else "",
                    "limit": str(limit_value),
                } if prev_page else {},
                "pager_next_action": "/audit" if next_page else "",
                "pager_next_fields": {
                    "page": str(next_page) if next_page else "",
                    "limit": str(limit_value),
                } if next_page else {},
                "pager_jump_action": "/audit",
                "pager_jump_fields": {
                    "limit": str(limit_value),
                },
            },
        },
    )


@app.post("/audit", response_class=HTMLResponse)
def audit_post(request: Request, page: Optional[str] = Form("1"), limit: Optional[str] = Form("50")):
    return audit(request, page=page, limit=limit)


@app.post("/tool/keyword-count", response_class=HTMLResponse)
def keyword_count(
    request: Request,
    keyword: str = Form(...),
    platform: Optional[str] = Form(None),
    store_code: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    start_date = parse_optional_date(start_date)
    end_date = parse_optional_date(end_date)
    platform = parse_optional_date(platform)
    store_code = parse_optional_date(store_code)

    keywords = [k.strip() for k in keyword.split("&") if k.strip()]
    if not keywords:
        return render_dashboard(request, {"errors": {"keyword_count": "关键词不能为空"}})

    select_parts = []
    params: List[Optional[str]] = []
    for kw in keywords:
        select_parts.append(
            sql.SQL(
                "SELECT %s AS keyword, raw_orders_keyword_count(%s, %s, %s, %s, %s) AS count"
            )
        )
        params.extend([kw, kw, start_date, end_date, platform, store_code])
    query = sql.SQL(" UNION ALL ").join(select_parts)
    try:
        columns, rows, has_more = run_query(query, tuple(params))
        log_audit(request, "keyword_count", f"keyword={keyword},platform={platform},store={store_code}")
        return render_dashboard(
            request,
            {
                "results": {"keyword_count": {"columns": columns, "rows": rows}},
                "has_more": {"keyword_count": has_more},
                "active_result": "keyword_count",
                "active_title": "关键词统计结果",
                "form": {
                    "keyword": keyword,
                    "platform": platform or "",
                    "store_code": store_code or "",
                    "start_date": start_date or "",
                    "end_date": end_date or "",
                },
            },
        )
    except Exception as exc:
        log_audit(request, "keyword_count", f"error={exc}")
        return render_dashboard(request, {"errors": {"keyword_count": str(exc)}})


@app.post("/tool/repeat-rate", response_class=HTMLResponse)
def repeat_rate(
    request: Request,
    platform: Optional[str] = Form(None),
    store_code: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    start_date = parse_optional_date(start_date)
    end_date = parse_optional_date(end_date)
    platform = parse_optional_date(platform)
    store_code = parse_optional_date(store_code)

    sql = "SELECT * FROM raw_orders_repeat_rate(%s, %s, %s, %s);"
    try:
        columns, rows, has_more = run_query(sql, (platform, store_code, start_date, end_date))
        log_audit(request, "repeat_rate", f"platform={platform},store={store_code}")
        return render_dashboard(
            request,
            {
                "results": {"repeat_rate": {"columns": columns, "rows": rows}},
                "has_more": {"repeat_rate": has_more},
                "active_result": "repeat_rate",
                "active_title": "复购率结果",
                "form": {
                    "rr_platform": platform or "",
                    "rr_store_code": store_code or "",
                    "rr_start_date": start_date or "",
                    "rr_end_date": end_date or "",
                },
            },
        )
    except Exception as exc:
        log_audit(request, "repeat_rate", f"error={exc}")
        return render_dashboard(request, {"errors": {"repeat_rate": str(exc)}})


@app.post("/tool/cross-store", response_class=HTMLResponse)
def cross_store(
    request: Request,
    store_code_a: str = Form(...),
    store_code_b: str = Form(...),
    platform: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    start_date = parse_optional_date(start_date)
    end_date = parse_optional_date(end_date)
    platform = parse_optional_date(platform)

    sql = "SELECT * FROM raw_orders_cross_store_customers(%s, %s, %s, %s, %s);"
    try:
        columns, rows, has_more = run_query(sql, (store_code_a, store_code_b, platform, start_date, end_date))
        log_audit(request, "cross_store", f"a={store_code_a},b={store_code_b},platform={platform}")
        return render_dashboard(
            request,
            {
                "results": {"cross_store": {"columns": columns, "rows": rows}},
                "has_more": {"cross_store": has_more},
                "active_result": "cross_store",
                "active_title": "交叉顾客结果",
                "form": {
                    "cs_store_code_a": store_code_a,
                    "cs_store_code_b": store_code_b,
                    "cs_platform": platform or "",
                    "cs_start_date": start_date or "",
                    "cs_end_date": end_date or "",
                },
            },
        )
    except Exception as exc:
        log_audit(request, "cross_store", f"error={exc}")
        return render_dashboard(request, {"errors": {"cross_store": str(exc)}})


@app.post("/tool/panda-phones", response_class=HTMLResponse)
def panda_phone_stats(
    request: Request,
    platform: Optional[str] = Form("panda"),
    store_code: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    start_date = parse_optional_date(start_date)
    end_date = parse_optional_date(end_date)
    platform = parse_optional_date(platform) or "panda"
    store_code = parse_optional_date(store_code)

    sql = """
        SELECT
            COUNT(*) AS total_values,
            COUNT(DISTINCT payload->'data'->'merchantOrderAddressResVO'->>'consigneeTelMask') AS distinct_values
        FROM raw_orders
        WHERE platform = %s
          AND (%s IS NULL OR store_code = %s)
          AND COALESCE(order_date::date, created_at::date) BETWEEN
              COALESCE(%s, date_trunc('month', CURRENT_DATE)::date)
              AND COALESCE(
                  %s,
                  (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::date
              )
          AND payload->'data'->'merchantOrderAddressResVO'->>'consigneeTelMask' IS NOT NULL;
    """
    try:
        columns, rows, has_more = run_query(sql, (platform, store_code, store_code, start_date, end_date))
        log_audit(request, "panda_phones", f"store={store_code}")
        return render_dashboard(
            request,
            {
                "results": {"panda_phones": {"columns": columns, "rows": rows}},
                "has_more": {"panda_phones": has_more},
                "active_result": "panda_phones",
                "active_title": "Panda 手机号掩码统计结果",
                "form": {
                    "pp_platform": platform,
                    "pp_store_code": store_code or "",
                    "pp_start_date": start_date or "",
                    "pp_end_date": end_date or "",
                },
            },
        )
    except Exception as exc:
        log_audit(request, "panda_phones", f"error={exc}")
        return render_dashboard(request, {"errors": {"panda_phones": str(exc)}})


@app.post("/tool/deliveroo-customers", response_class=HTMLResponse)
def deliveroo_customer_stats(
    request: Request,
    store_code: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    start_date = parse_optional_date(start_date)
    end_date = parse_optional_date(end_date)
    store_code = parse_optional_date(store_code)

    sql = """
        SELECT
            COUNT(*) AS total_values,
            COUNT(DISTINCT payload->'customer'->>'id') AS distinct_values
        FROM raw_orders
        WHERE platform = 'deliveroo'
          AND (%s IS NULL OR store_code = %s)
          AND COALESCE(order_date::date, created_at::date) BETWEEN
              COALESCE(%s, date_trunc('month', CURRENT_DATE)::date)
              AND COALESCE(
                  %s,
                  (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::date
              )
          AND payload->'customer'->>'id' IS NOT NULL;
    """
    try:
        columns, rows, has_more = run_query(sql, (store_code, store_code, start_date, end_date))
        log_audit(request, "deliveroo_customers", f"store={store_code}")
        return render_dashboard(
            request,
            {
                "results": {"deliveroo_customers": {"columns": columns, "rows": rows}},
                "has_more": {"deliveroo_customers": has_more},
                "active_result": "deliveroo_customers",
                "active_title": "Deliveroo 客户 ID 统计结果",
                "form": {
                    "dc_store_code": store_code or "",
                    "dc_start_date": start_date or "",
                    "dc_end_date": end_date or "",
                },
            },
        )
    except Exception as exc:
        log_audit(request, "deliveroo_customers", f"error={exc}")
        return render_dashboard(request, {"errors": {"deliveroo_customers": str(exc)}})


@app.post("/tool/sql-readonly", response_class=HTMLResponse)
def sql_readonly(
    request: Request,
    sql: str = Form(...),
    limit: Optional[str] = Form("200"),
    page: Optional[str] = Form("1"),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    allowed, error_msg, clean_sql = validate_readonly_sql(sql)
    if not allowed:
        log_audit(request, "sql_readonly", f"blocked={error_msg}")
        return render_dashboard(request, {"errors": {"sql_readonly": error_msg}, "form": {"sql_text": sql}})

    try:
        limit_value = clamp_limit(limit)
        page_value = clamp_page(page)
        offset = (page_value - 1) * limit_value
        count_sql = f"SELECT COUNT(*) FROM ({clean_sql}) AS t"
        count_columns, count_rows, _ = run_query_with_limit(count_sql, (), 1)
        total_count = count_rows[0][0] if count_rows else 0
        total_pages = max((total_count + limit_value - 1) // limit_value, 1)
        wrapped = f"SELECT * FROM ({clean_sql}) AS t LIMIT %s OFFSET %s"
        columns, rows, has_more = run_query_with_limit(wrapped, (limit_value, offset), limit_value)
        next_page = page_value + 1 if page_value < total_pages else None
        prev_page = page_value - 1 if page_value > 1 else None

        return render_dashboard(
            request,
            {
                "results": {"sql_readonly": {"columns": columns, "rows": rows}},
                "has_more": {"sql_readonly": has_more},
                "active_result": "sql_readonly",
                "active_title": "SQL 只读查询结果",
                "total_count": total_count,
                "total_pages": total_pages,
                "page_size": limit_value,
                "current_page": page_value,
                "form": {
                    "sql_text": sql,
                    "sql_limit": str(limit_value),
                    "sql_page": str(page_value),
                    "pager_prev_action": "/tool/sql-readonly" if prev_page else "",
                    "pager_prev_fields": {
                        "sql": sql,
                        "limit": str(limit_value),
                        "page": str(prev_page) if prev_page else "",
                    } if prev_page else {},
                    "pager_next_action": "/tool/sql-readonly" if next_page else "",
                    "pager_next_fields": {
                        "sql": sql,
                        "limit": str(limit_value),
                        "page": str(next_page) if next_page else "",
                    } if next_page else {},
                    "pager_jump_action": "/tool/sql-readonly",
                    "pager_jump_fields": {
                        "sql": sql,
                        "limit": str(limit_value),
                    },
                },
            },
        )
    except Exception as exc:
        log_audit(request, "sql_readonly", f"error={exc}")
        return render_dashboard(request, {"errors": {"sql_readonly": str(exc)}, "form": {"sql_text": sql}})


@app.post("/tool/export", response_class=HTMLResponse)
def export_csv(
    request: Request,
    kind: str = Form(...),
    table_name: Optional[str] = Form(None),
    view_name: Optional[str] = Form(None),
    sql_text: Optional[str] = Form(None),
    sort_by: Optional[str] = Form(None),
    sort_dir: Optional[str] = Form("asc"),
    limit: Optional[str] = Form("1000"),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    export_limit = min(max(int(limit or 1000), 1), 5000)
    sort_dir = (sort_dir or "asc").lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "asc"

    try:
        if kind == "preview_table" and table_name:
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
                raise ValueError("表名不合法")
            allowed_columns = get_relation_columns(table_name)
            if sort_by and sort_by not in allowed_columns:
                raise ValueError("排序字段不存在")
            order_sql = f" ORDER BY {sort_by} {sort_dir}" if sort_by else ""
            sql = f"SELECT * FROM {table_name}{order_sql} LIMIT %s"
            columns, rows, _ = run_query_with_limit(sql, (export_limit,), export_limit)
            log_audit(request, "export", f"table={table_name}")
            return build_csv_response(f"{table_name}.csv", columns, rows)

        if kind == "preview_view" and view_name:
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", view_name):
                raise ValueError("视图名不合法")
            allowed_columns = get_relation_columns(view_name)
            if sort_by and sort_by not in allowed_columns:
                raise ValueError("排序字段不存在")
            order_sql = f" ORDER BY {sort_by} {sort_dir}" if sort_by else ""
            sql = f"SELECT * FROM {view_name}{order_sql} LIMIT %s"
            columns, rows, _ = run_query_with_limit(sql, (export_limit,), export_limit)
            log_audit(request, "export", f"view={view_name}")
            return build_csv_response(f"{view_name}.csv", columns, rows)

        if kind == "sql_readonly" and sql_text:
            allowed, error_msg, clean_sql = validate_readonly_sql(sql_text)
            if not allowed:
                raise ValueError(error_msg)
            wrapped = f"SELECT * FROM ({clean_sql}) AS t LIMIT %s"
            columns, rows, _ = run_query_with_limit(wrapped, (export_limit,), export_limit)
            log_audit(request, "export", "sql")
            return build_csv_response("query.csv", columns, rows)

        raise ValueError("导出参数不完整")
    except Exception as exc:
        log_audit(request, "export", f"error={exc}")
        return render_dashboard(request, {"errors": {"export": str(exc)}})


@app.post("/tool/preview-table", response_class=HTMLResponse)
def preview_table(
    request: Request,
    table_name: str = Form(...),
    limit: Optional[int] = Form(50),
    sort_by: Optional[str] = Form(None),
    sort_dir: Optional[str] = Form("asc"),
    page: Optional[str] = Form("1"),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        return render_dashboard(request, {"errors": {"preview_table": "表名不合法"}})

    limit = clamp_limit(limit)
    page = clamp_page(page)
    sort_by = (sort_by or "").strip()
    sort_dir = (sort_dir or "asc").lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "asc"

    allowed_columns = get_relation_columns(table_name)
    if sort_by and sort_by not in allowed_columns:
        return render_dashboard(
            request,
            {
                "errors": {"preview_table": "排序字段不存在"},
                "form": {
                    "pt_table_name": table_name,
                    "pt_limit": str(limit),
                    "pt_sort_by": sort_by,
                    "pt_sort_dir": sort_dir,
                    "pt_page": str(page),
                },
                "pt_columns": allowed_columns,
            },
        )

    order_sql = f" ORDER BY {sort_by} {sort_dir}" if sort_by else ""
    offset = (page - 1) * limit
    count_sql = f"SELECT COUNT(*) FROM {table_name}"
    count_columns, count_rows, _ = run_query_with_limit(count_sql, (), 1)
    total_count = count_rows[0][0] if count_rows else 0
    total_pages = max((total_count + limit - 1) // limit, 1)
    sql = f"SELECT * FROM {table_name}{order_sql} LIMIT %s OFFSET %s"
    try:
        columns, rows, has_more = run_query_with_limit(sql, (limit, offset), limit)
        log_audit(request, "preview_table", f"table={table_name}")
        next_page = page + 1 if page < total_pages else None
        prev_page = page - 1 if page > 1 else None
        return render_dashboard(
            request,
            {
                "results": {"preview_table": {"columns": columns, "rows": rows}},
                "has_more": {"preview_table": has_more},
                "active_result": "preview_table",
                "active_title": "表格预览结果",
                "total_count": total_count,
                "total_pages": total_pages,
                "page_size": limit,
                "current_page": page,
                "form": {
                    "pt_table_name": table_name,
                    "pt_limit": str(limit),
                    "pt_sort_by": sort_by,
                    "pt_sort_dir": sort_dir,
                    "pt_page": str(page),
                    "pager_prev_action": "/tool/preview-table" if prev_page else "",
                    "pager_prev_fields": {
                        "table_name": table_name,
                        "limit": str(limit),
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                        "page": str(prev_page) if prev_page else "",
                    } if prev_page else {},
                    "pager_next_action": "/tool/preview-table" if next_page else "",
                    "pager_next_fields": {
                        "table_name": table_name,
                        "limit": str(limit),
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                        "page": str(next_page) if next_page else "",
                    } if next_page else {},
                    "pager_jump_action": "/tool/preview-table",
                    "pager_jump_fields": {
                        "table_name": table_name,
                        "limit": str(limit),
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                    },
                },
                "pt_columns": allowed_columns,
            },
        )
    except Exception as exc:
        log_audit(request, "preview_table", f"error={exc}")
        return render_dashboard(request, {"errors": {"preview_table": str(exc)}})


@app.post("/tool/preview-view", response_class=HTMLResponse)
def preview_view(
    request: Request,
    view_name: str = Form(...),
    limit: Optional[int] = Form(50),
    sort_by: Optional[str] = Form(None),
    sort_dir: Optional[str] = Form("asc"),
    page: Optional[str] = Form("1"),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", view_name):
        return render_dashboard(request, {"errors": {"preview_view": "视图名不合法"}})

    limit = clamp_limit(limit)
    page = clamp_page(page)
    sort_by = (sort_by or "").strip()
    sort_dir = (sort_dir or "asc").lower()
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "asc"

    allowed_columns = get_relation_columns(view_name)
    if sort_by and sort_by not in allowed_columns:
        return render_dashboard(
            request,
            {
                "errors": {"preview_view": "排序字段不存在"},
                "form": {
                    "pv_view_name": view_name,
                    "pv_limit": str(limit),
                    "pv_sort_by": sort_by,
                    "pv_sort_dir": sort_dir,
                    "pv_page": str(page),
                },
                "pv_columns": allowed_columns,
            },
        )

    order_sql = f" ORDER BY {sort_by} {sort_dir}" if sort_by else ""
    offset = (page - 1) * limit
    count_sql = f"SELECT COUNT(*) FROM {view_name}"
    count_columns, count_rows, _ = run_query_with_limit(count_sql, (), 1)
    total_count = count_rows[0][0] if count_rows else 0
    total_pages = max((total_count + limit - 1) // limit, 1)
    sql = f"SELECT * FROM {view_name}{order_sql} LIMIT %s OFFSET %s"
    try:
        columns, rows, has_more = run_query_with_limit(sql, (limit, offset), limit)
        log_audit(request, "preview_view", f"view={view_name}")
        next_page = page + 1 if page < total_pages else None
        prev_page = page - 1 if page > 1 else None
        return render_dashboard(
            request,
            {
                "results": {"preview_view": {"columns": columns, "rows": rows}},
                "has_more": {"preview_view": has_more},
                "active_result": "preview_view",
                "active_title": "视图预览结果",
                "total_count": total_count,
                "total_pages": total_pages,
                "page_size": limit,
                "current_page": page,
                "form": {
                    "pv_view_name": view_name,
                    "pv_limit": str(limit),
                    "pv_sort_by": sort_by,
                    "pv_sort_dir": sort_dir,
                    "pv_page": str(page),
                    "pager_prev_action": "/tool/preview-view" if prev_page else "",
                    "pager_prev_fields": {
                        "view_name": view_name,
                        "limit": str(limit),
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                        "page": str(prev_page) if prev_page else "",
                    } if prev_page else {},
                    "pager_next_action": "/tool/preview-view" if next_page else "",
                    "pager_next_fields": {
                        "view_name": view_name,
                        "limit": str(limit),
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                        "page": str(next_page) if next_page else "",
                    } if next_page else {},
                    "pager_jump_action": "/tool/preview-view",
                    "pager_jump_fields": {
                        "view_name": view_name,
                        "limit": str(limit),
                        "sort_by": sort_by,
                        "sort_dir": sort_dir,
                    },
                },
                "pv_columns": allowed_columns,
            },
        )
    except Exception as exc:
        log_audit(request, "preview_view", f"error={exc}")
        return render_dashboard(request, {"errors": {"preview_view": str(exc)}})
