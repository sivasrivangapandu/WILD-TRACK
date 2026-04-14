#!/usr/bin/env python3
"""
WildTrack AI - Interactive Render Deployment Wizard
Guides user through the entire deployment process step-by-step
"""

import os
import sys
import json
import webbrowser
import subprocess
from pathlib import Path
from typing import Optional

class RenderDeploymentWizard:
    """Interactive deployment guide"""
    
    def __init__(self):
        self.steps = []
        self.current_step = 0
        
    def print_header(self):
        print("\n" + "="*70)
        print("🚀 WILDTRACK AI - RENDER DEPLOYMENT WIZARD")
        print("="*70)
        print("\nThis wizard will guide you through deploying WildTrack AI to Render")
        print("in approximately 15 minutes.\n")
    
    def print_step_header(self, step_num: int, title: str):
        print(f"\n{'─'*70}")
        print(f"STEP {step_num}: {title}")
        print(f"{'─'*70}\n")
    
    def get_yes_no(self, prompt: str) -> bool:
        while True:
            response = input(f"{prompt} (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
    
    def run(self):
        """Run the deployment wizard"""
        self.print_header()
        
        # Step 1: Pre-flight checks
        self.print_step_header(1, "Pre-flight Checks")
        print("Verifying your system is ready for deployment...")
        
        if not self.verify_system():
            print("\n❌ Pre-flight checks failed. Please fix issues above and try again.")
            return False
        
        print("\n✅ Pre-flight checks passed!")
        
        # Step 2: Gather credentials
        self.print_step_header(2, "Gather Your API Credentials")
        print("You'll need the following credentials. Gather them now or paste them when asked:\n")
        print("1. GEMINI_API_KEY - Get from: https://makersuite.google.com/app/apikey")
        print("2. NINJA_API_KEY - Get from: https://api.api-ninjas.com/account")
        print("3. Cloudinary credentials (optional) - Get from: https://cloudinary.com")
        print("4. GitHub account access (for Render integration)")
        
        if not self.get_yes_no("\nDo you have all credentials ready?"):
            print("Please gather the above credentials and run this script again.")
            return False
        
        credentials = self.gather_credentials()
        
        # Step 3: Open Render dashboard
        self.print_step_header(3, "Create Backend Service")
        print("Opening Render dashboard in your browser...")
        webbrowser.open("https://dashboard.render.com")
        input("\n✓ Press Enter once you're logged into Render dashboard...")
        
        print("\nFollow these steps to create the backend service:")
        print("""
1. Click "New +" → "Web Service"
2. Select your WILD-TRACK repository
3. Name: wildtrack-backend
4. Build Command: cd backend && pip install -r requirements.txt
5. Start Command: cd backend && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
6. Choose Region: Oregon
7. Plan: Free (for now) or Starter ($7/month for production)
8. DON'T deploy yet - wait for next step
        """)
        
        input("\n✓ Press Enter once you've filled in all the settings...")
        
        # Step 4: Add environment variables
        self.print_step_header(4, "Add Backend Environment Variables")
        print("Now add these environment variables to your backend service:\n")
        
        env_vars = {
            "JWT_SECRET": self.generate_jwt_secret(),
            "GEMINI_API_KEY": credentials.get("gemini_api_key", ""),
            "NINJA_API_KEY": credentials.get("ninja_api_key", ""),
            "CLOUDINARY_CLOUD_NAME": credentials.get("cloudinary_cloud_name", ""),
            "CLOUDINARY_API_KEY": credentials.get("cloudinary_api_key", ""),
            "CLOUDINARY_API_SECRET": credentials.get("cloudinary_api_secret", ""),
            "CORS_ORIGINS": "https://wildtrack-frontend-iuww.onrender.com,http://localhost:3000",
            "PYTHON_VERSION": "3.10.0",
            "PORT": "8000"
        }
        
        for key, value in env_vars.items():
            if value:
                print(f"  {key}: {value if len(str(value)) < 40 else str(value)[:37] + '...'}")
            else:
                print(f"  {key}: (get from credentials)")
        
        print("\nAdd each key-value pair to the 'Environment' section in Render.")
        input("\n✓ Press Enter once you've added all environment variables...")
        
        # Step 5: Create frontend service
        self.print_step_header(5, "Create Frontend Service")
        print("Now create the frontend service:")
        print("""
1. Click "New +" → "Static Site"
2. Select your WILD-TRACK repository
3. Name: wildtrack-frontend
4. Build Command: cd frontend && npm install && npm ci --prefer-offline --no-audit && npm run build
5. Publish Directory: frontend/dist
6. Choose Region: Oregon
7. Plan: Free
        """)
        
        input("\n✓ Press Enter once you've created the frontend service...")
        
        # Step 6: Add frontend environment variables
        self.print_step_header(6, "Add Frontend Environment Variables")
        print("Add these to your frontend service:\n")
        print("  VITE_API_URL: https://wildtrack-backend-j9n8.onrender.com")
        print("  NODE_ENV: production")
        print("\n(Note: Replace backend URL with your actual backend URL from Render)")
        
        input("\n✓ Press Enter once you've added frontend environment variables...")
        
        # Step 7: Deploy
        self.print_step_header(7, "Deploy Services")
        print("Now click 'Deploy' on both services (if not already deployed).")
        print("\nExpected timeline:")
        print("  • Backend build: 5-10 minutes")
        print("  • Model downloads: 5-10 minutes")
        print("  • Frontend build: 3-5 minutes")
        print("  • Total: 15-20 minutes")
        
        input("\n✓ Press Enter once you've clicked Deploy on both services...")
        
        # Step 8: Monitor and test
        self.print_step_header(8, "Monitor & Test")
        print("The deployment is now running. Here's what to do:")
        print("""
MONITOR:
1. Watch backend logs for: "[MODEL] Loaded successfully"
2. Check frontend logs for build completion
3. Wait until both services show "Live"

TEST:
1. Test backend health: https://wildtrack-backend-j9n8.onrender.com/health
2. Open frontend: https://wildtrack-frontend-iuww.onrender.com
3. Try creating an account
4. Upload a footprint image
5. See your prediction result!
        """)
        
        print("\nDo you need help with testing?")
        if self.get_yes_no("Would you like to see the comprehensive testing guide?"):
            print("\nOpen: POST_DEPLOYMENT_TESTING.md for detailed testing procedures")
        
        # Step 9: Setup monitoring (optional)
        self.print_step_header(9, "Setup Monitoring (Optional but Recommended)")
        if self.get_yes_no("\nWould you like to setup uptime monitoring?"):
            webbrowser.open("https://uptimerobot.com")
            print("\n✓ Follow the UptimeRobot instructions to monitor your services")
            input("\nPress Enter once you've setup monitoring...")
        
        # Success!
        self.print_step_header(10, "🎉 DEPLOYMENT COMPLETE!")
        print("""
Congratulations! Your WildTrack AI system is now deployed to Render!

NEXT STEPS:
1. Monitor your services: https://dashboard.render.com
2. Check the testing guide: POST_DEPLOYMENT_TESTING.md
3. Setup monitoring alerts
4. Share with your users!

HELPFUL RESOURCES:
• Deployment Guide: PRODUCTION_DEPLOYMENT_GUIDE.md
• Testing Guide: POST_DEPLOYMENT_TESTING.md
• Monitoring Guide: PRODUCTION_MONITORING_GUIDE.md
• Environment Setup: ENVIRONMENT_SETUP_CHECKLIST.md

SUPPORT:
If you encounter issues, check the relevant guide for troubleshooting steps.
        """)
        
        return True
    
    def verify_system(self) -> bool:
        """Verify system is ready for deployment"""
        print("Checking repository status...")
        
        try:
            # Check git status
            result = subprocess.run(
                "git status --porcelain",
                shell=True,
                capture_output=True,
                text=True,
                cwd="d:\\Wild Track AI"
            )
            
            if "fatal" in result.stderr:
                print("❌ Not in a git repository")
                return False
            
            print("✅ Git repository found")
            
            # Check for required files
            required_files = [
                "render.yaml",
                "backend/main.py",
                "backend/requirements.txt",
                "frontend/src/main.jsx"
            ]
            
            for file in required_files:
                path = Path(f"d:\\Wild Track AI\\{file}")
                if path.exists():
                    print(f"✅ {file} found")
                else:
                    print(f"❌ {file} NOT found")
                    return False
            
            print("✅ All required files present")
            return True
            
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            return False
    
    def generate_jwt_secret(self) -> str:
        """Generate a random JWT secret"""
        import secrets
        import string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(chars) for _ in range(32))
    
    def gather_credentials(self) -> dict:
        """Gather credentials from user"""
        credentials = {}
        
        print("\n" + "="*70)
        print("Enter your credentials (or press Enter to skip optional ones):")
        print("="*70 + "\n")
        
        credentials["gemini_api_key"] = input("GEMINI_API_KEY: ").strip()
        credentials["ninja_api_key"] = input("NINJA_API_KEY: ").strip()
        credentials["cloudinary_cloud_name"] = input("CLOUDINARY_CLOUD_NAME (optional): ").strip()
        credentials["cloudinary_api_key"] = input("CLOUDINARY_API_KEY (optional): ").strip()
        credentials["cloudinary_api_secret"] = input("CLOUDINARY_API_SECRET (optional): ").strip()
        
        return credentials

def main():
    """Main entry point"""
    try:
        # Change to project directory
        os.chdir("d:\\Wild Track AI")
        
        wizard = RenderDeploymentWizard()
        success = wizard.run()
        
        if success:
            print("\n✅ Deployment wizard completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Deployment wizard cancelled or failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Wizard cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
