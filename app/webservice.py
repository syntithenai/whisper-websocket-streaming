import sys
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse

from fastapi import FastAPI, Request
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from webservice_streaming_routes import add_streaming_routes

app = FastAPI(
    title="Whisper Webservice",
    description='',
    version='0.0.1',
    contact={
        "url": ''
    },
    license_info={
        "name": "",
        "url": ''
    }
)

add_streaming_routes(app)



# cors headers for cross domain access
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.on_event('startup')
async def startup():
	print('startup')
	
@app.on_event('shutdown')
async def shutdown():
	print('shutdown')
	

@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
	# Change here to Logger
	print(str(exc))
	return JSONResponse(content="Something went wrong", status_code=500)
