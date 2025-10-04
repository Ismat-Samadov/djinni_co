import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from collections import Counter
import os
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# Create charts directory
os.makedirs('charts', exist_ok=True)

# Load data
with open('abysshub_products.json', 'r') as f:
    products = json.load(f)

with open('abysshub_threads_all.json', 'r') as f:
    threads = json.load(f)


# ============ CHART 1: Top 15 Widgets by Score ============
print("Creating Chart 1: Top Widgets by Score...")
df_products = pd.DataFrame(products)
top_widgets = df_products.nlargest(15, 'score')[['name', 'score', 'views', 'rate']]

fig, ax = plt.subplots(figsize=(14, 8))
bars = ax.barh(range(len(top_widgets)), top_widgets['score'], color='#4CAF50')
ax.set_yticks(range(len(top_widgets)))
ax.set_yticklabels([name[:40] + '...' if len(name) > 40 else name for name in top_widgets['name']], fontsize=9)
ax.set_xlabel('Score', fontweight='bold', fontsize=12)
ax.set_title('Top 15 Widgets by Score on AbyssHub', fontweight='bold', fontsize=14, pad=20)
ax.invert_yaxis()

# Add value labels
for i, (score, views, rate) in enumerate(zip(top_widgets['score'], top_widgets['views'], top_widgets['rate'])):
    ax.text(score + 0.01, i, f'{score:.2f} | {views}v | {rate}★',
            va='center', fontsize=8, color='#333')

plt.tight_layout()
plt.savefig('charts/01_top_widgets_by_score.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 2: Widget Tags Distribution ============
print("Creating Chart 2: Tag Distribution...")
all_tags = []
for product in products:
    all_tags.extend(product.get('tags', []))

tag_counts = Counter(all_tags).most_common(20)
tags, counts = zip(*tag_counts)

fig, ax = plt.subplots(figsize=(14, 8))
bars = ax.barh(range(len(tags)), counts, color='#2196F3')
ax.set_yticks(range(len(tags)))
ax.set_yticklabels(tags, fontsize=10)
ax.set_xlabel('Number of Widgets', fontweight='bold', fontsize=12)
ax.set_title('Top 20 Most Popular Tags on AbyssHub', fontweight='bold', fontsize=14, pad=20)
ax.invert_yaxis()

for i, count in enumerate(counts):
    ax.text(count + 0.3, i, str(count), va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('charts/02_tag_distribution.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 3: Views vs Rating Correlation ============
print("Creating Chart 3: Views vs Rating Correlation...")
df_products['rate_float'] = pd.to_numeric(df_products['rate'], errors='coerce')
df_clean = df_products[df_products['rate_float'] > 0].copy()

fig, ax = plt.subplots(figsize=(12, 8))
scatter = ax.scatter(df_clean['views'], df_clean['rate_float'],
                     c=df_clean['score'], cmap='viridis',
                     s=100, alpha=0.6, edgecolors='black', linewidth=0.5)
ax.set_xlabel('Views', fontweight='bold', fontsize=12)
ax.set_ylabel('Rating (Stars)', fontweight='bold', fontsize=12)
ax.set_title('Widget Performance: Views vs Rating (Color = Score)',
             fontweight='bold', fontsize=14, pad=20)
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Score', fontweight='bold', rotation=270, labelpad=20)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('charts/03_views_vs_rating.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 4: Thread Requests by Category ============
print("Creating Chart 4: Thread Categories...")
thread_tags = []
for thread in threads:
    thread_tags.extend(thread.get('tags', []))

thread_tag_counts = Counter(thread_tags).most_common(15)
t_tags, t_counts = zip(*thread_tag_counts)

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.bar(range(len(t_tags)), t_counts, color='#FF5722', alpha=0.8, edgecolor='black')
ax.set_xticks(range(len(t_tags)))
ax.set_xticklabels(t_tags, rotation=45, ha='right', fontsize=10)
ax.set_ylabel('Number of Requests', fontweight='bold', fontsize=12)
ax.set_title('User Demand: Top 15 Request Categories (Threads)',
             fontweight='bold', fontsize=14, pad=20)

for i, count in enumerate(t_counts):
    ax.text(i, count + 0.2, str(count), ha='center', va='bottom',
            fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('charts/04_thread_categories.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 5: Price Distribution ============
print("Creating Chart 5: Price Distribution...")
free_count = sum(1 for p in products if p['byssium_price'] == 0)
paid_count = len(products) - free_count
paid_prices = [p['byssium_price'] for p in products if p['byssium_price'] > 0]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Pie chart
ax1.pie([free_count, paid_count], labels=['Free', 'Paid'],
        autopct='%1.1f%%', colors=['#4CAF50', '#FFC107'],
        startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
ax1.set_title('Widget Pricing Model Distribution', fontweight='bold', fontsize=12)

# Histogram for paid widgets
if paid_prices:
    ax2.hist(paid_prices, bins=10, color='#9C27B0', edgecolor='black', alpha=0.7)
    ax2.set_xlabel('Price (Byssium)', fontweight='bold', fontsize=11)
    ax2.set_ylabel('Number of Widgets', fontweight='bold', fontsize=11)
    ax2.set_title(f'Paid Widget Price Distribution (n={len(paid_prices)})',
                  fontweight='bold', fontsize=12)
    ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('charts/05_price_distribution.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 6: Top Creators ============
print("Creating Chart 6: Top Creators...")
creators = Counter([p['user']['username'] for p in products]).most_common(10)
usernames, widget_counts = zip(*creators)

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.bar(range(len(usernames)), widget_counts, color='#00BCD4',
              alpha=0.8, edgecolor='black')
ax.set_xticks(range(len(usernames)))
ax.set_xticklabels(usernames, rotation=45, ha='right', fontsize=10)
ax.set_ylabel('Number of Widgets', fontweight='bold', fontsize=12)
ax.set_title('Top 10 Widget Creators on AbyssHub', fontweight='bold', fontsize=14, pad=20)

for i, count in enumerate(widget_counts):
    ax.text(i, count + 0.3, str(count), ha='center', va='bottom',
            fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('charts/06_top_creators.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 7: PDF-Related Analysis ============
print("Creating Chart 7: PDF Widget Analysis...")
pdf_widgets = [p for p in products if 'pdf' in ' '.join(p.get('tags', [])).lower() or
               'pdf' in p['name'].lower()]

categories = {
    'PDF Conversion': 0,
    'PDF Extraction': 0,
    'PDF Analysis': 0,
    'PDF Generation': 0,
    'Other PDF': 0
}

for widget in pdf_widgets:
    name_desc = (widget['name'] + ' ' + widget['meta_description']).lower()
    if 'convert' in name_desc or 'converter' in name_desc:
        categories['PDF Conversion'] += 1
    elif 'extract' in name_desc or 'extractor' in name_desc:
        categories['PDF Extraction'] += 1
    elif 'analyz' in name_desc or 'analysis' in name_desc:
        categories['PDF Analysis'] += 1
    elif 'generat' in name_desc:
        categories['PDF Generation'] += 1
    else:
        categories['Other PDF'] += 1

fig, ax = plt.subplots(figsize=(10, 10))
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
wedges, texts, autotexts = ax.pie(categories.values(), labels=categories.keys(),
                                    autopct='%1.0f%%', colors=colors, startangle=90,
                                    textprops={'fontsize': 11, 'fontweight': 'bold'})
ax.set_title(f'PDF Widget Categories (Total: {len(pdf_widgets)} widgets)',
             fontweight='bold', fontsize=14, pad=20)

for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(12)

plt.tight_layout()
plt.savefig('charts/07_pdf_categories.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ CHART 8: Engagement Metrics Heatmap ============
print("Creating Chart 8: Engagement Heatmap...")
top_20 = df_products.nlargest(20, 'score')[['name', 'score', 'views', 'rate', 'mention_count']]
top_20['rate_float'] = pd.to_numeric(top_20['rate'], errors='coerce')

# Normalize for heatmap
heatmap_data = top_20[['score', 'views', 'rate_float', 'mention_count']].copy()
heatmap_data = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())

fig, ax = plt.subplots(figsize=(10, 14))
sns.heatmap(heatmap_data.T, cmap='RdYlGn', annot=False, cbar_kws={'label': 'Normalized Value'},
            xticklabels=[name[:25] + '...' if len(name) > 25 else name for name in top_20['name']],
            yticklabels=['Score', 'Views', 'Rating', 'Mentions'], ax=ax)
ax.set_title('Top 20 Widgets: Engagement Metrics Heatmap', fontweight='bold', fontsize=14, pad=20)
plt.xticks(rotation=90, fontsize=8)
plt.yticks(fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig('charts/08_engagement_heatmap.png', dpi=300, bbox_inches='tight')
plt.close()


# ============ Generate Statistics Summary ============
print("\nGenerating statistics summary...")

stats = {
    'total_widgets': len(products),
    'total_threads': len(threads),
    'avg_widget_rating': df_clean['rate_float'].mean(),
    'avg_views': df_products['views'].mean(),
    'total_tags': len(set(all_tags)),
    'free_widgets': free_count,
    'paid_widgets': paid_count,
    'pdf_widgets': len(pdf_widgets),
    'ai_widgets': sum(1 for p in products if 'ai' in ' '.join(p.get('tags', [])).lower()),
    'top_tag': tag_counts[0][0] if tag_counts else 'N/A',
    'most_viewed_widget': df_products.nlargest(1, 'views').iloc[0]['name'],
    'highest_rated': df_clean.nlargest(1, 'rate_float').iloc[0]['name']
}

with open('charts/statistics.json', 'w') as f:
    json.dump(stats, f, indent=2)

print(f"\n✅ All charts saved to ./charts/")
print(f"📊 Statistics saved to ./charts/statistics.json")
print(f"\nKey Findings:")
print(f"  • Total Widgets: {stats['total_widgets']}")
print(f"  • Total User Requests (Threads): {stats['total_threads']}")
print(f"  • Average Rating: {stats['avg_widget_rating']:.2f}★")
print(f"  • PDF-Related Widgets: {stats['pdf_widgets']}")
print(f"  • AI-Powered Widgets: {stats['ai_widgets']}")
print(f"  • Most Popular Tag: '{stats['top_tag']}'")
