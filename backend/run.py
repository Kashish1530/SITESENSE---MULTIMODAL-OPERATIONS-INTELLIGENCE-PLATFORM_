import uvicorn
from app.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print("=" * 65)
    print(f"  {settings.PROJECT_NAME}")
    print("=" * 65)
    print(f"  * Home Page:    http://localhost:{settings.PORT}")
    print(f"  * Swagger Docs: http://localhost:{settings.PORT}/docs")
    print(f"  * Health Check: http://localhost:{settings.PORT}/api/v1/health")
    print("=" * 65)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
