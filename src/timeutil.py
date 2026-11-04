from datetime import datetime
FMT = "%Y-%m-%dT%H:%M:%SZ"
def fmt(dt): return dt.strftime(FMT) if dt else None
def parse(s): return datetime.strptime(s, FMT) if s else None
