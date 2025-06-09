#!/usr/bin/env python3
"""
Enthusiasm Log Viewer - Tool for analyzing enthusiasm scoring logs

Features:
- View recent enthusiasm scoring decisions
- Filter by score ranges, decisions, channels
- Summary statistics
- Export filtered results
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse


class EnthusiasmLogViewer:
    """Utility for viewing and analyzing enthusiasm scoring logs"""
    
    def __init__(self, log_dir: str = "logs/enthusiasm"):
        self.log_dir = Path(log_dir)
        if not self.log_dir.exists():
            print(f"❌ Log directory not found: {log_dir}")
            sys.exit(1)
    
    def get_log_files(self, days: int = 7) -> List[Path]:
        """Get log files from the last N days"""
        files = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            log_file = self.log_dir / f"enthusiasm_{date}.jsonl"
            if log_file.exists():
                files.append(log_file)
        return files
    
    def load_entries(self, files: List[Path]) -> List[Dict[str, Any]]:
        """Load all log entries from files"""
        entries = []
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
            except Exception as e:
                print(f"⚠️  Error reading {file}: {e}")
        
        # Sort by timestamp
        entries.sort(key=lambda x: x.get('timestamp', ''))
        return entries
    
    def filter_entries(self, entries: List[Dict], **filters) -> List[Dict]:
        """Filter entries based on criteria"""
        filtered = entries.copy()
        
        if 'min_score' in filters:
            filtered = [e for e in filtered if e.get('result', {}).get('parsed_score', 0) >= filters['min_score']]
        
        if 'max_score' in filters:
            filtered = [e for e in filtered if e.get('result', {}).get('parsed_score', 9) <= filters['max_score']]
        
        if 'decision' in filters:
            filtered = [e for e in filtered if e.get('result', {}).get('decision', '') == filters['decision']]
        
        if 'channel' in filters:
            filtered = [e for e in filtered if filters['channel'].lower() in e.get('message_context', {}).get('channel', '').lower()]
        
        if 'author' in filters:
            filtered = [e for e in filtered if filters['author'].lower() in e.get('message_context', {}).get('author', '').lower()]
        
        return filtered
    
    def print_summary(self, entries: List[Dict]):
        """Print summary statistics"""
        if not entries:
            print("📊 No entries found")
            return
        
        total = len(entries)
        responded = len([e for e in entries if e.get('result', {}).get('decision') == 'RESPOND'])
        skipped = total - responded
        
        scores = [e.get('result', {}).get('parsed_score', 0) for e in entries]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        channels = set(e.get('message_context', {}).get('channel', '') for e in entries)
        authors = set(e.get('message_context', {}).get('author', '') for e in entries)
        
        print(f"""
📊 **Enthusiasm Scoring Summary**

**Decisions:**
  • Total messages analyzed: {total}
  • Responded: {responded} ({responded/total*100:.1f}%)
  • Skipped: {skipped} ({skipped/total*100:.1f}%)

**Scores:**
  • Average score: {avg_score:.1f}
  • Score range: {min(scores)}-{max(scores)}
  • Score distribution:
    • 0-2: {len([s for s in scores if s <= 2])} messages
    • 3-5: {len([s for s in scores if 3 <= s <= 5])} messages  
    • 6-8: {len([s for s in scores if 6 <= s <= 8])} messages
    • 9: {len([s for s in scores if s == 9])} messages

**Activity:**
  • Unique channels: {len(channels)}
  • Unique authors: {len(authors)}
  • Time range: {entries[0].get('timestamp', 'Unknown')} to {entries[-1].get('timestamp', 'Unknown')}
""")
    
    def print_entries(self, entries: List[Dict], limit: int = 10, verbose: bool = False):
        """Print individual log entries"""
        print(f"\n📝 **Recent Entries** (showing {min(limit, len(entries))} of {len(entries)})\n")
        
        for i, entry in enumerate(entries[-limit:], 1):
            timestamp = entry.get('timestamp', 'Unknown')
            result = entry.get('result', {})
            msg_ctx = entry.get('message_context', {})
            analysis = entry.get('analysis', {})
            
            score = result.get('parsed_score', 0)
            decision = result.get('decision', 'UNKNOWN')
            decision_emoji = "✅" if decision == "RESPOND" else "❌"
            
            print(f"{decision_emoji} **#{i} - Score: {score}/9 → {decision}**")
            print(f"   ⏰ {timestamp}")
            print(f"   👤 {msg_ctx.get('author', 'Unknown')} in #{msg_ctx.get('channel', 'Unknown')}")
            print(f"   💬 \"{msg_ctx.get('content', '')[:100]}...\"")
            
            if verbose:
                print(f"   🤖 Raw response: \"{result.get('raw_response', '')}\"")
                print(f"   📊 Analysis: {analysis.get('messages_since_last_bot', 0)} msgs since bot, active_convo: {analysis.get('active_conversation', False)}")
                print(f"   🔍 Mentioned: {msg_ctx.get('is_mentioned', False)}, Other bots: {analysis.get('other_bots_count', 0)}")
            
            print()
    
    def export_csv(self, entries: List[Dict], filename: str):
        """Export entries to CSV for analysis"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'timestamp', 'score', 'decision', 'threshold', 'author', 'channel',
                'content_preview', 'is_mentioned', 'messages_since_bot', 'active_conversation',
                'other_bots_count', 'raw_response'
            ])
            
            # Data
            for entry in entries:
                result = entry.get('result', {})
                msg_ctx = entry.get('message_context', {})
                analysis = entry.get('analysis', {})
                
                writer.writerow([
                    entry.get('timestamp', ''),
                    result.get('parsed_score', 0),
                    result.get('decision', ''),
                    entry.get('threshold', 0),
                    msg_ctx.get('author', ''),
                    msg_ctx.get('channel', ''),
                    msg_ctx.get('content', '')[:100],
                    msg_ctx.get('is_mentioned', False),
                    analysis.get('messages_since_last_bot', 0),
                    analysis.get('active_conversation', False),
                    analysis.get('other_bots_count', 0),
                    result.get('raw_response', '')
                ])
        
        print(f"📁 Exported {len(entries)} entries to {filename}")


def main():
    parser = argparse.ArgumentParser(description="View and analyze enthusiasm scoring logs")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--limit", type=int, default=10, help="Number of entries to show (default: 10)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")
    parser.add_argument("--min-score", type=int, help="Filter by minimum score")
    parser.add_argument("--max-score", type=int, help="Filter by maximum score")
    parser.add_argument("--decision", choices=["RESPOND", "SKIP"], help="Filter by decision")
    parser.add_argument("--channel", help="Filter by channel name (partial match)")
    parser.add_argument("--author", help="Filter by author name (partial match)")
    parser.add_argument("--export", help="Export to CSV file")
    parser.add_argument("--log-dir", default="logs/enthusiasm", help="Log directory path")
    
    args = parser.parse_args()
    
    viewer = EnthusiasmLogViewer(args.log_dir)
    
    # Load entries
    log_files = viewer.get_log_files(args.days)
    if not log_files:
        print(f"❌ No log files found in {args.log_dir} for the last {args.days} days")
        return
    
    print(f"📂 Loading from {len(log_files)} log files...")
    entries = viewer.load_entries(log_files)
    
    if not entries:
        print("❌ No log entries found")
        return
    
    # Apply filters
    filters = {}
    if args.min_score is not None:
        filters['min_score'] = args.min_score
    if args.max_score is not None:
        filters['max_score'] = args.max_score
    if args.decision:
        filters['decision'] = args.decision
    if args.channel:
        filters['channel'] = args.channel
    if args.author:
        filters['author'] = args.author
    
    if filters:
        entries = viewer.filter_entries(entries, **filters)
        print(f"🔍 Applied filters: {filters}")
    
    # Show results
    viewer.print_summary(entries)
    viewer.print_entries(entries, args.limit, args.verbose)
    
    # Export if requested
    if args.export:
        viewer.export_csv(entries, args.export)


if __name__ == "__main__":
    main()