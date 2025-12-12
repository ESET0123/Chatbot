
import sqlite3
import sys

DB_PATH = "./../mydata.db"

def clear_conversation_tables():
    """
    Empty user_conversations and conversation_history tables
    """
    print("=" * 60)
    print("🗑️  CLEARING CONVERSATION TABLES")
    print("=" * 60)
    
    # Confirmation prompt
    print("\n⚠️  WARNING: This will delete ALL conversations and history!")
    print("This action CANNOT be undone.\n")
    
    confirm = input("Type 'YES' to confirm deletion: ")
    
    if confirm != "YES":
        print("❌ Operation cancelled.")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check current counts
        cur.execute("SELECT COUNT(*) FROM conversation_history")
        history_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM user_conversations")
        conversations_count = cur.fetchone()[0]
        
        print(f"\n📊 Current data:")
        print(f"   - Conversation history entries: {history_count}")
        print(f"   - User conversations: {conversations_count}")
        
        if history_count == 0 and conversations_count == 0:
            print("\n✅ Tables are already empty!")
            conn.close()
            return
        
        # Delete conversation history first (because of foreign key)
        print("\n🗑️  Deleting conversation history...")
        cur.execute("DELETE FROM conversation_history")
        deleted_history = cur.rowcount
        print(f"   ✓ Deleted {deleted_history} history entries")
        
        # Delete user conversations
        print("🗑️  Deleting user conversations...")
        cur.execute("DELETE FROM user_conversations")
        deleted_conversations = cur.rowcount
        print(f"   ✓ Deleted {deleted_conversations} conversations")
        
        # Commit the changes
        conn.commit()
        
        # Verify deletion
        cur.execute("SELECT COUNT(*) FROM conversation_history")
        remaining_history = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM user_conversations")
        remaining_conversations = cur.fetchone()[0]
        
        print(f"\n📊 After deletion:")
        print(f"   - Conversation history entries: {remaining_history}")
        print(f"   - User conversations: {remaining_conversations}")
        
        if remaining_history == 0 and remaining_conversations == 0:
            print("\n✅ Successfully cleared all conversation tables!")
        else:
            print("\n⚠️  Warning: Some entries may remain")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    
    print("=" * 60)


def clear_for_specific_user(user_id):
    """
    Clear conversations for a specific user only
    """
    print("=" * 60)
    print(f"🗑️  CLEARING CONVERSATIONS FOR USER {user_id}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
        
        if not user:
            print(f"❌ User with ID {user_id} not found!")
            conn.close()
            return
        
        print(f"\n👤 User: {user[0]}")
        
        # Count current entries
        cur.execute("SELECT COUNT(*) FROM conversation_history WHERE user_id = ?", (user_id,))
        history_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM user_conversations WHERE user_id = ?", (user_id,))
        conversations_count = cur.fetchone()[0]
        
        print(f"\n📊 Current data:")
        print(f"   - Conversation history entries: {history_count}")
        print(f"   - User conversations: {conversations_count}")
        
        if history_count == 0 and conversations_count == 0:
            print("\n✅ User has no conversations!")
            conn.close()
            return
        
        confirm = input(f"\nType 'YES' to delete all conversations for user {user_id}: ")
        
        if confirm != "YES":
            print("❌ Operation cancelled.")
            conn.close()
            return
        
        # Delete for specific user
        print("\n🗑️  Deleting conversation history...")
        cur.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
        deleted_history = cur.rowcount
        print(f"   ✓ Deleted {deleted_history} history entries")
        
        print("🗑️  Deleting user conversations...")
        cur.execute("DELETE FROM user_conversations WHERE user_id = ?", (user_id,))
        deleted_conversations = cur.rowcount
        print(f"   ✓ Deleted {deleted_conversations} conversations")
        
        conn.commit()
        print("\n✅ Successfully cleared conversations for this user!")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    
    print("=" * 60)


def show_statistics():
    """
    Show statistics about conversations
    """
    print("=" * 60)
    print("📊 CONVERSATION STATISTICS")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Total conversations
        cur.execute("SELECT COUNT(*) FROM user_conversations")
        total_conversations = cur.fetchone()[0]
        
        # Total history entries
        cur.execute("SELECT COUNT(*) FROM conversation_history")
        total_history = cur.fetchone()[0]
        
        # Conversations per user
        cur.execute("""
            SELECT u.email, COUNT(uc.conversation_id) as conv_count
            FROM users u
            LEFT JOIN user_conversations uc ON u.id = uc.user_id
            GROUP BY u.id, u.email
            ORDER BY conv_count DESC
        """)
        user_stats = cur.fetchall()
        
        print(f"\n📈 Overall Statistics:")
        print(f"   - Total conversations: {total_conversations}")
        print(f"   - Total history entries: {total_history}")
        
        print(f"\n👥 Conversations per user:")
        for email, count in user_stats:
            print(f"   - {email}: {count} conversations")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    
    print("=" * 60)


def main():
    """
    Main function with menu
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            clear_conversation_tables()
        elif sys.argv[1] == "--user" and len(sys.argv) > 2:
            user_id = int(sys.argv[2])
            clear_for_specific_user(user_id)
        elif sys.argv[1] == "--stats":
            show_statistics()
        else:
            print("Usage:")
            print("  python clear_conversations.py --all              # Clear all conversations")
            print("  python clear_conversations.py --user <user_id>   # Clear for specific user")
            print("  python clear_conversations.py --stats            # Show statistics")
    else:
        print("=" * 60)
        print("🗑️  CONVERSATION TABLE MANAGER")
        print("=" * 60)
        print("\nOptions:")
        print("1. Clear ALL conversations (all users)")
        print("2. Clear conversations for specific user")
        print("3. Show statistics")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            clear_conversation_tables()
        elif choice == "2":
            show_statistics()
            user_id = input("\nEnter user ID to clear: ")
            try:
                clear_for_specific_user(int(user_id))
            except ValueError:
                print("❌ Invalid user ID!")
        elif choice == "3":
            show_statistics()
        elif choice == "4":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice!")


if __name__ == "__main__":
    main()