"""
GitHub Utils - Interaction directe avec GitHub API
==================================================
Permet à Claude de lire, modifier et commiter les fichiers directement sur GitHub
Sans passer par /mnt/project/ ou outputs intermédiaires

Usage:
    from github_utils import GitHubManager
    
    gh = GitHubManager(
        token="ghp_...",
        owner="SoeuriseSCI",
        repo="head-soeurise-module1"
    )
    
    # Lire un fichier
    content = gh.read_file("module2_workflow_v2_CORRECTED.py")
    
    # Modifier et commiter
    gh.update_file(
        filename="module2_workflow_v2_CORRECTED.py",
        new_content=modified_content,
        commit_message="Fix: bug dans DetecteurTypeEvenement"
    )
"""

import requests
import base64
import json
from typing import Dict, Optional, Tuple


class GitHubManager:
    """Gestionnaire d'accès direct à GitHub via API"""
    
    def __init__(self, token: str, owner: str, repo: str):
        """
        Initialise le gestionnaire GitHub
        
        Args:
            token: GitHub personal access token (GITHUB_TOKEN)
            owner: Propriétaire du repo (ex: "SoeuriseSCI")
            repo: Nom du repo (ex: "head-soeurise-module1")
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def read_file(self, filename: str) -> Tuple[bool, str, Optional[str]]:
        """
        Lit un fichier depuis GitHub
        
        Args:
            filename: Chemin du fichier (ex: "module2_workflow_v2_CORRECTED.py")
        
        Returns:
            (succès, contenu, sha)
            - succès: True si OK, False sinon
            - contenu: Le contenu du fichier (ou message d'erreur)
            - sha: Le SHA du fichier (nécessaire pour update)
        """
        try:
            url = f"{self.base_url}/contents/{filename}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 404:
                return False, f"❌ Fichier '{filename}' non trouvé sur GitHub", None
            
            if response.status_code != 200:
                return False, f"❌ Erreur API GitHub ({response.status_code}): {response.text[:200]}", None
            
            data = response.json()
            
            # Le contenu est en base64
            if 'content' not in data:
                return False, "❌ Pas de contenu dans la réponse GitHub", None
            
            content = base64.b64decode(data['content']).decode('utf-8')
            sha = data['sha']
            
            return True, content, sha
        
        except Exception as e:
            return False, f"❌ Erreur lecture GitHub: {str(e)[:100]}", None
    
    def update_file(self, filename: str, new_content: str, commit_message: str,
                    author_name: str = "_Head.Soeurise",
                    author_email: str = "u6334452013@gmail.com") -> Tuple[bool, str]:
        """
        Modifie un fichier sur GitHub et crée un commit
        
        Args:
            filename: Chemin du fichier
            new_content: Le nouveau contenu
            commit_message: Message du commit
            author_name: Nom de l'auteur (par défaut: _Head.Soeurise)
            author_email: Email de l'auteur
        
        Returns:
            (succès, message)
        """
        try:
            # 1. Lire le fichier courant pour obtenir le SHA
            success, content, sha = self.read_file(filename)
            
            if not success:
                return False, f"❌ Impossible de lire {filename}: {content}"
            
            if not sha:
                return False, f"❌ Pas de SHA pour {filename}"
            
            # 2. Préparer le contenu encodé en base64
            content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            
            # 3. Préparer la requête de mise à jour
            url = f"{self.base_url}/contents/{filename}"
            
            payload = {
                "message": commit_message,
                "content": content_b64,
                "sha": sha,
                "author": {
                    "name": author_name,
                    "email": author_email
                },
                "committer": {
                    "name": author_name,
                    "email": author_email
                }
            }
            
            # 4. Envoyer la mise à jour
            response = requests.put(url, headers=self.headers, json=payload)
            
            if response.status_code not in [200, 201]:
                return False, f"❌ Erreur mise à jour GitHub ({response.status_code}): {response.text[:300]}"
            
            data = response.json()
            commit_sha = data.get('commit', {}).get('sha', 'unknown')
            
            return True, f"✅ Fichier '{filename}' mis à jour sur GitHub\n   Commit: {commit_sha[:8]}"
        
        except Exception as e:
            return False, f"❌ Erreur mise à jour GitHub: {str(e)[:200]}"
    
    def create_file(self, filename: str, content: str, commit_message: str,
                    author_name: str = "_Head.Soeurise",
                    author_email: str = "u6334452013@gmail.com") -> Tuple[bool, str]:
        """
        Crée un nouveau fichier sur GitHub
        
        Args:
            filename: Chemin du fichier
            content: Contenu du fichier
            commit_message: Message du commit
            author_name: Nom de l'auteur
            author_email: Email de l'auteur
        
        Returns:
            (succès, message)
        """
        try:
            url = f"{self.base_url}/contents/{filename}"
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            payload = {
                "message": commit_message,
                "content": content_b64,
                "author": {
                    "name": author_name,
                    "email": author_email
                },
                "committer": {
                    "name": author_name,
                    "email": author_email
                }
            }
            
            response = requests.put(url, headers=self.headers, json=payload)
            
            if response.status_code not in [201, 200]:
                return False, f"❌ Erreur création GitHub ({response.status_code}): {response.text[:300]}"
            
            data = response.json()
            commit_sha = data.get('commit', {}).get('sha', 'unknown')
            
            return True, f"✅ Fichier '{filename}' créé sur GitHub\n   Commit: {commit_sha[:8]}"
        
        except Exception as e:
            return False, f"❌ Erreur création GitHub: {str(e)[:200]}"
    
    def list_files(self, path: str = "") -> Tuple[bool, list]:
        """
        Liste les fichiers dans le repo
        
        Args:
            path: Chemin optionnel (ex: "module2/")
        
        Returns:
            (succès, liste_fichiers)
        """
        try:
            url = f"{self.base_url}/contents/{path}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return False, []
            
            data = response.json()
            files = [f['name'] for f in data if f['type'] == 'file']
            
            return True, files
        
        except Exception as e:
            return False, []


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFACE SIMPLIFIÉE POUR CLAUDE
# ═══════════════════════════════════════════════════════════════════════════════

def init_github_from_env():
    """
    Initialise GitHubManager à partir des variables d'environnement
    
    Nécessite:
    - GITHUB_TOKEN
    
    Returns:
        GitHubManager ou None si erreur
    """
    import os
    
    token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        print("❌ GITHUB_TOKEN non défini dans les variables d'environnement")
        return None
    
    return GitHubManager(
        token=token,
        owner="SoeuriseSCI",
        repo="head-soeurise-module1"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST & DÉMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    
    token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        print("❌ GITHUB_TOKEN non défini")
        print("\nUsage:")
        print("  export GITHUB_TOKEN='ghp_...'")
        print("  python github_utils.py")
        exit(1)
    
    print("🔧 Initialisation GitHub Manager...")
    gh = GitHubManager(
        token=token,
        owner="SoeuriseSCI",
        repo="head-soeurise-module1"
    )
    
    print("\n📝 Test: Lecture du fichier README.md")
    success, content, sha = gh.read_file("README.md")
    
    if success:
        print(f"✅ Fichier lu avec succès ({len(content)} chars)")
        print(f"   SHA: {sha[:8]}...")
        print(f"   Contenu (premiers 200 chars):\n{content[:200]}")
    else:
        print(f"❌ Erreur: {content}")
    
    print("\n📂 Test: Lister les fichiers")
    success, files = gh.list_files()
    if success:
        print(f"✅ Fichiers trouvés: {', '.join(files[:5])}")
    else:
        print("❌ Erreur listing")
