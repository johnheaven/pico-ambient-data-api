from mini_server.mini_server import mini_server
from callbacks.callbacks import Callbacks
from helpers.bits_and_bobs import RuntimeParams

### DEFINE SIMPLE TEST FUNCTION ###

def test(correct, result):
    try:
        assert result == correct
    except AssertionError as e:
        print('Correct: ', correct)
        print('Result: ', result)
        raise e

## SETUP ###

runtime_params = RuntimeParams

callbacks = Callbacks(valid_kinds=('route', 'callback'), runtime_params_obj=runtime_params)

ms = mini_server([], callbacks_obj=callbacks, runtime_params_obj=runtime_params)

### TESTS ###

# __add_runtime_param
correct = {'test': 'testtext'}
result = ms.__add_runtime_param('test', 'testtext')
test(correct, result)

correct = {'test': 'testtext', 'test_2': [1, 2, 3]}
result = ms.__add_runtime_param('test_2', [1, 2, 3])
test(correct, result)

# __get_runtime_params
result = callbacks.__get_runtime_params(('test', 'test_2'), {'idontknow': 'whatever'})
correct = {'test': 'testtext', 'test_2': [1, 2, 3], 'idontknow': 'whatever'}
test(correct, result)

# add_callback
dummy = lambda: True
ms.add_callback('test', dummy, {'abc': 123}, runtime_params=(1,2,3))
result = ms.callbacks
correct = [('test', dummy, {'abc': 123}, (1,2,3))]
test(correct, result)

print('All tests passed!')
