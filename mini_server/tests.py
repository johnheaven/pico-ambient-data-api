from mini_server.mini_server import mini_server

def test(correct, result):
    try:
        assert result == correct
    except AssertionError as e:
        print('Correct: ', correct)
        print('Result: ', result)
        raise e

ms = mini_server([])

# __add_placeholder_param
correct = {'test': 'testtext'}
result = ms.__add_placeholder_param('test', 'testtext')
test(correct, result)

correct = {'test': 'testtext', 'test_2': [1, 2, 3]}
result = ms.__add_placeholder_param('test_2', [1, 2, 3])
test(correct, result)

# __get_placeholder_params
result = ms.__get_placeholder_params(('test', 'test_2'), {'idontknow': 'whatever'})
correct = {'test': 'testtext', 'test_2': [1, 2, 3], 'idontknow': 'whatever'}
test(correct, result)

# add_callback
dummy = lambda: True
ms.add_callback('test', dummy, {'abc': 123}, placeholder_params=(1,2,3))
result = ms.callbacks
correct = [('test', dummy, {'abc': 123}, (1,2,3))]
test(correct, result)

# handler mapping
handlers = ms.callbacks
handlers = tuple(
    map(
        # both need to be tuples to add them, hence the brackets. This is essentially replacing the last two items (params and placeholder_params with a merged dict of the two)
        # ... but with placeholder_params now a dictionary with the placeholders filled in
        lambda handler: handler[:-2] + (ms.__get_placeholder_params(keys=handler[-1], merge=handler[-2]),),
        handlers
        )
    )
result = handlers
correct = (('test', dummy, {'abc': 123},),)
print('All tests passed!')
