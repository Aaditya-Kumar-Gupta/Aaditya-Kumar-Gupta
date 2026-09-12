import json, os, urllib.request
from collections import Counter
from datetime import datetime, timezone
from xml.sax.saxutils import escape

USER = "Aaditya-Kumar-Gupta"
OUT = "profile-cards"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
HEAD = {"Accept": "application/vnd.github+json", "User-Agent": "profile-card-generator"}
if TOKEN:
    HEAD["Authorization"] = f"Bearer {TOKEN}"

os.makedirs(OUT, exist_ok=True)

def get(url):
    req = urllib.request.Request(url, headers=HEAD)
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def graphql(query):
    data = json.dumps({"query": query}).encode()
    h = dict(HEAD); h["Content-Type"] = "application/json"
    req = urllib.request.Request("https://api.github.com/graphql", data=data, headers=h, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def svg(name, body, w=800, h=220):
    open(f"{OUT}/{name}", "w", encoding="utf-8").write(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" rx="12" fill="#1a1b26"/><style>text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.t{{fill:#a9b1d6}}.v{{fill:#7aa2f7;font-weight:700}}.s{{fill:#73daca}}</style>{body}</svg>''')

def text(x,y,s,c='t',size=16,anchor='start'):
    return f'<text x="{x}" y="{y}" class="{c}" font-size="{size}" text-anchor="{anchor}">{escape(str(s))}</text>'

user = get(f"{API}/users/{USER}")
repos = get(f"{API}/users/{USER}/repos?per_page=100&type=owner&sort=updated")
public_repos = user.get("public_repos", 0)
followers = user.get("followers", 0)
following = user.get("following", 0)
stars = sum(r.get("stargazers_count",0) for r in repos)

# Languages from owned repositories.
langs = Counter()
for r in repos:
    try:
        for k,v in get(r["languages_url"]).items(): langs[k] += v
    except Exception: pass
total = sum(langs.values()) or 1
lang_rows = sorted(langs.items(), key=lambda x:x[1], reverse=True)[:8]

# Contribution data (requires the workflow's normal GitHub token).
contrib = {"totalCommitContributions":0,"totalIssueContributions":0,"totalPullRequestContributions":0,"totalRepositoryContributions":0,"restrictedContributionsCount":0,"contributionCalendar":{"totalContributions":0,"weeks":[]}}
try:
    q='''query { user(login:"%s") { contributionsCollection { totalCommitContributions totalIssueContributions totalPullRequestContributions totalRepositoryContributions restrictedContributionsCount contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } } } } }''' % USER
    contrib = graphql(q)["data"]["user"]["contributionsCollection"]
except Exception: pass

body = text(32,40,"GitHub Stats",'t',20)
items=[("Repositories",public_repos),("Followers",followers),("Following",following),("Stars Earned",stars),("Contributions (year)",contrib.get("contributionCalendar",{}).get("totalContributions",0))]
for i,(label,val) in enumerate(items):
    x=35+(i%3)*255; y=82+(i//3)*70
    body += text(x,y,val,'v',28)+text(x,y+24,label,'t',13)
svg("stats.svg",body,800,220)

body=text(32,38,"Top Languages",'t',20)
for i,(lang,n) in enumerate(lang_rows):
    y=68+i*18; pct=n/total*100
    body += text(35,y+12,lang,'t',13)+f'<rect x="150" y="{y}" width="500" height="12" rx="6" fill="#292e42"/><rect x="150" y="{y}" width="{500*pct/100:.1f}" height="12" rx="6" fill="#7aa2f7"/>'+text(670,y+12,f"{pct:.1f}%",'s',12)
svg("languages.svg",body,760,max(190,70+len(lang_rows)*18))

# Contribution calendar, generated locally from GitHub's API data.
days=[]
for week in contrib.get("contributionCalendar",{}).get("weeks",[]): days.extend(week.get("contributionDays",[]))
levels=[0,1,3,6,10]
def level(n): return sum(n>=x for x in levels)-1
body=text(30,34,"Contribution Activity",'t',20)+text(30,55,f"{len(days)} days • {contrib.get('contributionCalendar',{}).get('totalContributions',0)} contributions",'s',12)
startx,starty=30,70
for i,d in enumerate(days[-364:]):
    x=startx+(i//7)*12; y=starty+(i%7)*12
    n=d.get("contributionCount",0); lv=level(n)
    fill=['#16161e','#1f3a36','#285f4f','#3b8f6e','#73daca'][max(0,lv)]
    body += f'<rect x="{x}" y="{y}" width="9" height="9" rx="2" fill="{fill}"/>'
svg("activity.svg",body,760,175)

body=text(30,40,"GitHub Achievements",'t',20)
for i,(label,val) in enumerate([("Commits",contrib.get("totalCommitContributions",0)),("Issues",contrib.get("totalIssueContributions",0)),("Pull Requests",contrib.get("totalPullRequestContributions",0)),("Repositories",contrib.get("totalRepositoryContributions",0))]):
    x=35+i*185; body+=f'<circle cx="{x+45}" cy="105" r="38" fill="#24283b" stroke="#bb9af7" stroke-width="3"/>'+text(x+45,112,val,'v',23,'middle')+text(x+45,165,label,'t',12,'middle')
svg("trophy.svg",body,800,190)

projects=[("PDFPilot","Python • PySide6/Qt","aaditya-kumar-gupta.github.io/PDFPilot/"),("real-time_weather-app","React • Node.js • MongoDB","aditya-weather-app.vercel.app"),("NewsHub","JavaScript • HTML • CSS","news-hub.page.gd")]
for repo,stack,url in projects:
    try: r=get(f"{API}/repos/{USER}/{repo}")
    except Exception: r={"stargazers_count":0,"forks_count":0,"description":""}
    body=text(28,42,repo,'v',22)+text(28,72,stack,'s',14)+text(28,110,(r.get('description') or 'GitHub project')[:85],'t',13)+text(28,155,f"★ {r.get('stargazers_count',0)}    Forks {r.get('forks_count',0)}",'t',13)+text(28,188,url,'s',12)
    safe=repo.replace('/','-')
    svg(f"project-{safe}.svg",body,760,215)
