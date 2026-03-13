import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def set_user_role(email, role):
    """
    Sets the role for a user ensuring they exist in the 'users' collection.
    Since we don't have a direct email-to-uid mapping in Firestore unless we query,
    we have to query the users collection by email or use Admin Auth to find UID.
    """
    try:
        # 1. User UID 찾기 (Firebase Authentication이 아니라 Firestore Users 컬렉션에서)
        # Auth에서 찾으려면 auth.get_user_by_email()을 써야 하지만, 여기선 Firestore 문서 업데이트가 목적임.
        # 앱 로직상 'users' 컬렉션 문서는 로그인 시 생성됨. (uid 문서)
        
        # Firestore에서 email 필드로 쿼리
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        docs = query.stream()
        
        user_doc = None
        for doc in docs:
            user_doc = doc
            break
            
        if not user_doc:
            print(f"[Error] User with email '{email}' not found in Firestore.")
            print("The user must sign in at least once to create their record.")
            return

        # 2. 역할 업데이트
        user_ref = users_ref.document(user_doc.id)
        user_ref.update({'role': role})
        print(f"[Success] Updated role for {email} to '{role}'.")

    except Exception as e:
        print(f"[Error] An error occurred: {e}")

if __name__ == "__main__":
    print("=== MesuGak Role Manager ===")
    print("Available Roles: 'member' (Blocked), 'user' (Approved), 'admin' (Master)")
    
    target_email = input("Enter user email: ").strip()
    target_role = input("Enter new role: ").strip()
    
    if target_role not in ['member', 'user', 'admin']:
        print("[Error] Invalid role. Choose from 'member', 'user', 'admin'.")
    else:
        set_user_role(target_email, target_role)
