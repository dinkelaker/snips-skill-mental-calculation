#!/usr/bin/env python2
from hermes_python.hermes import Hermes
import random

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

INTENT_START = "bezzam:start_mental_calculations"
INTENT_ANSWER = "bezzam:give_mental_calculation"
INTENT_STOP = "bezzam:stop_lesson"
INTENT_DOES_NOT_KNOW = "bezzam:does_not_know_calculation"

INTENT_FILTER_GET_ANSWER = [
    INTENT_ANSWER,
    INTENT_STOP,
    INTENT_DOES_NOT_KNOW
]

operations = ["add", "sub", "mul", "div"]

SessionsStates = {}


def create_question(oper=None):

    if oper is None or oper not in operations:
        oper = random.choice(operations)

    x = random.randint(2, 12)
    y = random.randint(2, 12)

    # make sure the answer is a positive integer
    question = None
    answer = None
    if oper == "add":
        answer = x + y
        question = "What is {} plus {}?".format(x, y)
    elif oper == "sub":
        answer = x
        x = x + y
        question = "What is {} minus {}?".format(x, y)
    elif oper == "mul":
        answer = x * y
        question = "What is {} times {}?".format(x, y)
    elif oper == "div":
        answer = x
        x = x * y
        question = "What is {} divided by {}?".format(x, y)

    return question, answer


def continue_lesson(response, session_id):
    SessionsStates[session_id]["step"] += 1

    if SessionsStates[session_id]["step"] == SessionsStates[session_id]["n_questions"]:
        response += "You had {} out of {} correct. ".format(SessionsStates[session_id]["good"],
                                                                             SessionsStates[session_id]["n_questions"])
        percent_correct = float(SessionsStates[session_id]["good"]) / SessionsStates[session_id]["n_questions"]
        if percent_correct == 1.:
            response += "You are so smart!"
        elif percent_correct >= 0.75:
            response += "Well done! With a bit more practice you'll be a master."
        elif percent_correct >= 0.5:
            response += "Not bad. With more practice, you'll get better."
        else:
            response += "You should really practice more."
        del SessionsStates[session_id]
        cont = False
    else:
        question, answer = create_question()
        response += question
        SessionsStates[session_id]["ans"] = answer
        cont = True

    return response, cont


def user_request_quiz(hermes, intent_message):
    session_id = intent_message.session_id

    # parse input message, NOTE extra space to append question
    n_questions = int(intent_message.slots.n_questions.first().value)
    if n_questions > 1:
        response = "Starting a lesson with {} questions. ".format(n_questions) //the white space after the full stop leads to a spoken break
    elif n_questions == 1:
        response = "Starting a lesson with one question. "
    else:
        response = "I can only give a positive number of questions."
        hermes.publish_end_session(session_id, response)

    # create first question
    question, answer = create_question()

    # initialize session state
    session_state = {
        "ans": answer,
        "good": 0,
        "bad": 0,
        "step": 0,
        "n_questions": n_questions
    }
    SessionsStates[session_id] = session_state

    hermes.publish_continue_session(session_id, response + question, INTENT_FILTER_GET_ANSWER)


def user_gives_answer(hermes, intent_message):
    session_id = intent_message.session_id

    # parse input message
    answer = intent_message.slots.answer.first().value

    # check user answer, NOTE the extra space at the end since we will add more to the response!
    if answer == SessionsStates[session_id]["ans"]:
        response = "Correct! "
        SessionsStates[session_id]["good"] += 1
    else:
        response = "Incorrect. The answer is {}. ".format(SessionsStates[session_id]["ans"])
        SessionsStates[session_id]["bad"] += 1
        #import sounddevice
        #sd.play("file.wav")
        #response+ = ""
        #hermes.publish_end_session(session_id, response)

    # create new question or terminate if reached desired number of questions
    response, cont = continue_lesson(response, session_id)
    if cont:
        hermes.publish_continue_session(intent_message.session_id, response, INTENT_FILTER_GET_ANSWER)
    else:
        hermes.publish_end_session(session_id, response)


def user_does_not_know(hermes, intent_message):
    session_id = intent_message.session_id

    response = "That's quite alright! The answer is {}. ".format(SessionsStates[session_id]["ans"])

    # create new question or terminate if reached desired number of questions
    response, cont = continue_lesson(response, session_id)
    if cont:
        hermes.publish_continue_session(intent_message.session_id, response, INTENT_FILTER_GET_ANSWER)
    else:
        hermes.publish_end_session(session_id, response)


def user_quits(hermes, intent_message):
    session_id = intent_message.session_id

    # clean up
    del SessionsStates[session_id]
    response = "Alright. Let's play again soon!"

    hermes.publish_end_session(session_id, response)


with Hermes(MQTT_ADDR) as h:

    h.subscribe_intent(INTENT_START, user_request_quiz) \
        .subscribe_intent(INTENT_STOP, user_quits) \
        .subscribe_intent(INTENT_DOES_NOT_KNOW, user_does_not_know) \
        .subscribe_intent(INTENT_ANSWER, user_gives_answer) \
        .start()
