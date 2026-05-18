import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
const firebaseConfig = {
  apiKey: "AIzaSyDv36_HH-eXmHmGCBSoVic7sAQSbZrldyc",
  authDomain: "studio-5459225470-8cee2.firebaseapp.com",
  projectId: "studio-5459225470-8cee2",
  storageBucket: "studio-5459225470-8cee2.firebasestorage.app",
  messagingSenderId: "11096865451",
  appId: "1:11096865451:web:cc4be03668b581bf5495ee"
};


import { getAuth, GoogleAuthProvider } from "firebase/auth";

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();