import json
import os
import time
import uuid
from copy import deepcopy
import csv
import sys
import pathlib

import boto3
import dash
import dash_core_components as dcc
import dash_html_components as html
import requests
from dash.dependencies import Input, Output, State
from flask_caching import Cache

import dash_reusable_components as drc
import utils

DEBUG = True
LOCAL = False
APP_PATH = str(pathlib.Path(__file__).parent.resolve())

app = dash.Dash(__name__)
server = app.server

LOCAL = True
# Caching with filesystem when served locally
cache_config = {
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": os.path.join(APP_PATH, "data"),
}

# Empty cache directory before running the app
folder = os.path.join(APP_PATH, "data")
for the_file in os.listdir(folder):
    file_path = os.path.join(folder, the_file)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(e)

# If local, image data is stored locally in image_string.csv
f = open("image_string.csv", "w+")
f.close()

# Store images are very long strings, so allowed csv
# reading length is increased to its maximum allowed value
maxInt = sys.maxsize
while True:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt / 10)

# Caching
cache = Cache()
cache.init_app(app.server, config=cache_config)


# Store key value value (session_id, stringed_image)
def store_image_string(string_image, key_name):
    if DEBUG:
        print(key_name)
    # If local, the string is stored in image_string.csv
    if LOCAL:
        with open("image_string.csv", mode="w+") as image_file:
            image_writer = csv.DictWriter(image_file,
                                          fieldnames=["key", "image"])
            image_writer.writeheader()
            image_writer.writerow(dict(key=key_name, image=string_image))
    # Generate the POST attributes
    else:
        post = s3.generate_presigned_post(Bucket=bucket_name, Key=key_name)

        files = {"file": string_image}
        # Post the string file using requests
        requests.post(post["url"], data=post["fields"], files=files)


def serve_layout():
    # Generates a session ID
    session_id = str(uuid.uuid4())

    # Post the image to the right key, inside the bucket named after the
    # session ID
    store_image_string(utils.IMAGE_STRING_PLACEHOLDER, session_id)

    # App Layout
    return html.Div(
        id="root",
        children=[
            # Session ID
            html.Div(session_id, id="session-id"),
            # Main body
            html.Div(
                id="app-container",
                children=[
                    # Banner display
                    html.Div(
                        id="banner",
                        children=[
                            html.H2("Image Processing And Visualization App",
                                    id="title"),
                        ],
                    ),
                    html.Div(
                        id="image",
                        children=[
                            # The Interactive Image Div contains the dcc Graph
                            # showing the image, as well as the hidden div storing
                            # the true image
                            html.Div(
                                id="div-interactive-image",
                                children=[
                                    utils.GRAPH_PLACEHOLDER,
                                    html.Div(
                                        id="div-storage",
                                        children=utils.STORAGE_PLACEHOLDER,
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
            # Sidebar
            html.Div(
                id="sidebar",
                children=[
                    drc.Card([
                        dcc.Upload(
                            id="upload-image",
                            children=[
                                "Drag and Drop or ",
                                html.A(children="Select an Image"),
                            ],
                            # No CSS alternative here
                            style={
                                "color": "darkgray",
                                "width": "100%",
                                "height": "50px",
                                "lineHeight": "50px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "borderColor": "darkgray",
                                "textAlign": "center",
                                "padding": "2rem 0",
                                "margin-bottom": "2rem",
                            },
                            accept="image/*",
                        ),
                        drc.NamedInlineRadioItems(
                            name="Selection Mode",
                            short="selection-mode",
                            options=[
                                {
                                    "label": " Rectangular",
                                    "value": "select"
                                },
                                {
                                    "label": " Lasso",
                                    "value": "lasso"
                                },
                            ],
                            val="select",
                        ),
                        drc.NamedInlineRadioItems(
                            name="Image Display Format",
                            short="encoding-format",
                            options=[
                                {
                                    "label": " JPEG",
                                    "value": "jpeg"
                                },
                                {
                                    "label": " PNG",
                                    "value": "png"
                                },
                            ],
                            val="jpeg",
                        ),
                    ]),
                    drc.Card([
                        drc.CustomDropdown(
                            id="dropdown-filters",
                            options=[
                                {
                                    "label": "Blur",
                                    "value": "blur"
                                },
                                {
                                    "label": "Contour",
                                    "value": "contour"
                                },
                                {
                                    "label": "Detail",
                                    "value": "detail"
                                },
                                {
                                    "label": "Enhance Edge",
                                    "value": "edge_enhance"
                                },
                                {
                                    "label": "Enhance Edge (More)",
                                    "value": "edge_enhance_more",
                                },
                                {
                                    "label": "Emboss",
                                    "value": "emboss"
                                },
                                {
                                    "label": "Find Edges",
                                    "value": "find_edges"
                                },
                                {
                                    "label": "Sharpen",
                                    "value": "sharpen"
                                },
                                {
                                    "label": "Smooth",
                                    "value": "smooth"
                                },
                                {
                                    "label": "Smooth (More)",
                                    "value": "smooth_more"
                                },
                            ],
                            searchable=False,
                            placeholder="Basic Filter...",
                        ),
                        drc.CustomDropdown(
                            id="dropdown-enhance",
                            options=[
                                {
                                    "label": "Brightness",
                                    "value": "brightness"
                                },
                                {
                                    "label": "Color Balance",
                                    "value": "color"
                                },
                                {
                                    "label": "Contrast",
                                    "value": "contrast"
                                },
                                {
                                    "label": "Sharpness",
                                    "value": "sharpness"
                                },
                            ],
                            searchable=False,
                            placeholder="Enhance...",
                        ),
                        html.Div(
                            id="div-enhancement-factor",
                            children=[
                                f"Enhancement Factor:",
                                html.Div(children=dcc.Slider(
                                    id="slider-enhancement-factor",
                                    min=0,
                                    max=2,
                                    step=0.1,
                                    value=1,
                                    updatemode="drag",
                                )),
                            ],
                        ),
                        html.Div(
                            id="button-group",
                            children=[
                                html.Button("Run Operation",
                                            id="button-run-operation"),
                                html.Button("Undo", id="button-undo"),
                            ],
                        ),
                    ]),
                    dcc.Graph(
                        id="graph-histogram-colors",
                        figure={
                            "layout": {
                                "paper_bgcolor": "#272a31",
                                "plot_bgcolor": "#272a31",
                            }
                        },
                        config={"displayModeBar": False},
                    ),
                ],
            ),
        ],
    )


app.layout = serve_layout


# Helper functions for callbacks
def add_action_to_stack(action_stack, operation, operation_type, selectedData):
    """
    Add new action to the action stack, in-place.
    :param action_stack: The stack of action that are applied to an image
    :param operation: The operation that is applied to the image
    :param operation_type: The type of the operation, which could be a filter,
    an enhancement, etc.
    :param selectedData: The JSON object that contains the zone selected by
    the user in which the operation is applied
    :return: None, appending is done in place
    """

    new_action = {
        "operation": operation,
        "type": operation_type,
        "selectedData": selectedData,
    }

    action_stack.append(new_action)


def undo_last_action(n_clicks, storage):
    action_stack = storage["action_stack"]

    if n_clicks is None:
        storage["undo_click_count"] = 0

    # If the stack isn't empty and the undo click count has changed
    elif len(action_stack) > 0 and n_clicks > storage["undo_click_count"]:
        # Remove the last action on the stack
        action_stack.pop()

        # Update the undo click count
        storage["undo_click_count"] = n_clicks

    return storage


# Recursively retrieve the previous versions of the image by popping the
# action stack
@cache.memoize()
def apply_actions_on_image(session_id, action_stack, filename,
                           image_signature):
    action_stack = deepcopy(action_stack)

    # If we have arrived to the original image
    if len(action_stack) == 0 and LOCAL:
        with open("image_string.csv", mode="r") as image_file:
            image_reader = csv.DictReader(image_file)
            for row in image_reader:
                im_pil = drc.b64_to_pil(row["image"])
                return im_pil

    if len(action_stack) == 0 and not LOCAL:
        # Retrieve the url in which the image string is stored inside s3,
        # using the session ID

        url = s3.generate_presigned_url(ClientMethod="get_object",
                                        Params={
                                            "Bucket": bucket_name,
                                            "Key": session_id
                                        })

        # A key replacement is required for URL pre-sign in gcp

        url = url.replace("AWSAccessKeyId", "GoogleAccessId")

        response = requests.get(url)
        if DEBUG:
            print("IMAGE STRING LENGTH: " + str(len(response.text)))
        im_pil = drc.b64_to_pil(response.text)
        return im_pil

    # Pop out the last action
    last_action = action_stack.pop()
    # Apply all the previous action_stack recursively, and gets the image PIL
    im_pil = apply_actions_on_image(session_id, action_stack, filename,
                                    image_signature)
    im_size = im_pil.size

    # Apply the rest of the action_stack
    operation = last_action["operation"]
    selected_data = last_action["selectedData"]
    action_type = last_action["type"]

    # Select using Lasso
    if selected_data and "lassoPoints" in selected_data:
        selection_mode = "lasso"
        selection_zone = utils.generate_lasso_mask(im_pil, selected_data)
    # Select using rectangular box
    elif selected_data and "range" in selected_data:
        selection_mode = "select"
        lower, upper = map(int, selected_data["range"]["y"])
        left, right = map(int, selected_data["range"]["x"])
        # Adjust height difference
        height = im_size[1]
        upper = height - upper
        lower = height - lower
        selection_zone = (left, upper, right, lower)
    # Select the whole image
    else:
        selection_mode = "select"
        selection_zone = (0, 0) + im_size

    # Apply the filters
    if action_type == "filter":
        utils.apply_filters(image=im_pil,
                            zone=selection_zone,
                            filter=operation,
                            mode=selection_mode)
    elif action_type == "enhance":
        enhancement = operation["enhancement"]
        factor = operation["enhancement_factor"]

        utils.apply_enhancements(
            image=im_pil,
            zone=selection_zone,
            enhancement=enhancement,
            enhancement_factor=factor,
            mode=selection_mode,
        )

    return im_pil


@app.callback(
    Output("interactive-image", "figure"),
    [Input("radio-selection-mode", "value")],
    [State("interactive-image", "figure")],
)
def update_selection_mode(selection_mode, figure):
    if figure:
        figure["layout"]["dragmode"] = selection_mode
    return figure


@app.callback(Output("graph-histogram-colors", "figure"),
              [Input("interactive-image", "figure")])
def update_histogram(figure):
    # Retrieve the image stored inside the figure
    enc_str = figure["layout"]["images"][0]["source"].split(";base64,")[-1]
    # Creates the PIL Image object from the b64 png encoding
    im_pil = drc.b64_to_pil(string=enc_str)

    return utils.show_histogram(im_pil)


@app.callback(
    Output("div-interactive-image", "children"),
    [
        Input("upload-image", "contents"),
        Input("button-undo", "n_clicks"),
        Input("button-run-operation", "n_clicks"),
    ],
    [
        State("interactive-image", "selectedData"),
        State("dropdown-filters", "value"),
        State("dropdown-enhance", "value"),
        State("slider-enhancement-factor", "value"),
        State("upload-image", "filename"),
        State("radio-selection-mode", "value"),
        State("radio-encoding-format", "value"),
        State("div-storage", "children"),
        State("session-id", "children"),
    ],
)
def update_graph_interactive_image(
    content,
    undo_clicks,
    n_clicks,
    # new_win_width,
    selectedData,
    filters,
    enhance,
    enhancement_factor,
    new_filename,
    dragmode,
    enc_format,
    storage,
    session_id,
):
    t_start = time.time()

    # Retrieve information saved in storage, which is a dict containing
    # information about the image and its action stack
    storage = json.loads(storage)
    filename = storage["filename"]  # Filename is the name of the image file.
    image_signature = storage["image_signature"]

    # Runs the undo function if the undo button was clicked. Storage stays
    # the same otherwise.
    storage = undo_last_action(undo_clicks, storage)

    # If a new file was uploaded (new file name changed)
    if new_filename and new_filename != filename:
        # Replace filename
        if DEBUG:
            print(filename, "replaced by", new_filename)

        # Update the storage dict
        storage["filename"] = new_filename

        # Parse the string and convert to pil
        string = content.split(";base64,")[-1]
        im_pil = drc.b64_to_pil(string)

        # Update the image signature, which is the first 200 b64 characters
        # of the string encoding
        storage["image_signature"] = string[:200]

        # Posts the image string into the Bucketeer Storage (which is hosted
        # on S3)
        store_image_string(string, session_id)
        if DEBUG:
            print(new_filename, "added to Bucketeer S3.")

        # Resets the action stack
        storage["action_stack"] = []

    # If an operation was applied (when the filename wasn't changed)
    else:
        # Add actions to the action stack (we have more than one if filters
        # and enhance are BOTH selected)
        if filters:
            type = "filter"
            operation = filters
            add_action_to_stack(storage["action_stack"], operation, type,
                                selectedData)

        if enhance:
            type = "enhance"
            operation = {
                "enhancement": enhance,
                "enhancement_factor": enhancement_factor,
            }
            add_action_to_stack(storage["action_stack"], operation, type,
                                selectedData)

        # Apply the required actions to the picture, using memoized function
        im_pil = apply_actions_on_image(session_id, storage["action_stack"],
                                        filename, image_signature)

    t_end = time.time()
    if DEBUG:
        print(f"Updated Image Storage in {t_end - t_start:.3f} sec")

    return [
        drc.InteractiveImagePIL(
            image_id="interactive-image",
            image=im_pil,
            enc_format=enc_format,
            dragmode=dragmode,
            verbose=DEBUG,
        ),
        html.Div(id="div-storage",
                 children=json.dumps(storage),
                 style={"display": "none"}),
    ]


# Show/Hide Callbacks
@app.callback(
    Output("div-enhancement-factor", "style"),
    [Input("dropdown-enhance", "value")],
    [State("div-enhancement-factor", "style")],
)
def show_slider_enhancement_factor(value, style):
    # If any enhancement is selected
    if value:
        style["display"] = "block"
    else:
        style["display"] = "none"

    return style


# Reset Callbacks
@app.callback(Output("dropdown-filters", "value"),
              [Input("button-run-operation", "n_clicks")])
def reset_dropdown_filters(_):
    return None


@app.callback(Output("dropdown-enhance", "value"),
              [Input("button-run-operation", "n_clicks")])
def reset_dropdown_enhance(_):
    return None


# Running the server
if __name__ == "__main__":
    app.run_server(debug=True)
